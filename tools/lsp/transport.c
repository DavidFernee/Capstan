/* capstan-lsp transport: the only part of the language server not written in Capstan.
 *
 * The language server protocol frames each message as "Content-Length: N\r\n\r\n"
 * followed by N bytes with no line break after them. Capstan's runtime can read
 * standard input only a line at a time (read_line), and its standard output is
 * buffered until the program exits, so a Capstan program on its own would wait
 * forever for a newline the editor never sends, and the editor would wait forever
 * for a reply still sitting in the buffer. Until the runtime gains a bounded byte
 * read and a flush, this shim bridges the gap. It knows nothing about the
 * protocol: every framing decision, size limit and JSON check is made in
 * tools/lsp.cap.
 *
 *   - the child process runs the Capstan server (its main() is renamed
 *     capstan_lsp_main at build time) with standard output unbuffered, so each
 *     message it prints reaches the editor at once;
 *   - this process copies the editor's bytes to the child as escaped lines: each
 *     chunk read becomes one line, with '\\' written as "\\\\" and a newline as
 *     "\\n", so read_line() returns every chunk as soon as it arrives, unchanged
 *     after unescaping.
 *
 * When the editor closes its end the child sees end of input and exits; when the
 * child exits (after an "exit" notification) this process exits with its status.
 */
#include <errno.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

int capstan_lsp_main(int argc, char **argv);

static int write_all(int fd, const unsigned char *p, size_t n) {
    while (n > 0) {
        ssize_t w = write(fd, p, n);
        if (w < 0) {
            if (errno == EINTR) continue;
            return -1;
        }
        p += w;
        n -= (size_t)w;
    }
    return 0;
}

static int status_of(int st) {
    if (WIFEXITED(st)) return WEXITSTATUS(st);
    if (WIFSIGNALED(st)) return 128 + WTERMSIG(st);
    return 1;
}

int main(int argc, char **argv) {
    int p[2];
    if (pipe(p) != 0) {
        perror("capstan-lsp: pipe");
        return 1;
    }
    fflush(stdout);
    pid_t pid = fork();
    if (pid < 0) {
        perror("capstan-lsp: fork");
        return 1;
    }
    if (pid == 0) {
        if (dup2(p[0], 0) < 0) _exit(1);
        close(p[0]);
        close(p[1]);
        setvbuf(stdout, NULL, _IONBF, 0);
        exit(capstan_lsp_main(argc, argv));
    }
    close(p[0]);
    signal(SIGPIPE, SIG_IGN);
    static unsigned char in[65536];
    static unsigned char out[2 * sizeof in + 1];
    int st = 0;
    for (;;) {
        pid_t done = waitpid(pid, &st, WNOHANG);
        if (done == pid) return status_of(st);
        struct pollfd pfd = {0, POLLIN, 0};
        int r = poll(&pfd, 1, 100);
        if (r < 0 && errno != EINTR) break;
        if (r <= 0) continue;
        ssize_t n = read(0, in, sizeof in);
        if (n < 0 && (errno == EINTR || errno == EAGAIN)) continue;
        if (n <= 0) break;
        size_t m = 0;
        for (ssize_t i = 0; i < n; i++) {
            if (in[i] == '\\') { out[m++] = '\\'; out[m++] = '\\'; }
            else if (in[i] == '\n') { out[m++] = '\\'; out[m++] = 'n'; }
            else out[m++] = in[i];
        }
        out[m++] = '\n';
        if (write_all(p[1], out, m) != 0) break;
    }
    close(p[1]);
    while (waitpid(pid, &st, 0) < 0) {
        if (errno != EINTR) return 1;
    }
    return status_of(st);
}
