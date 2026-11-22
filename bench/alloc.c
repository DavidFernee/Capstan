/* malloc/free equivalent (manual memory management). */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
typedef struct T { struct T *l, *r; } T;
static T *make(int d) { T *t = malloc(sizeof(T)); t->l = d ? make(d - 1) : NULL; t->r = d ? make(d - 1) : NULL; return t; }
static int64_t count(T *t) { return t ? 1 + count(t->l) + count(t->r) : 0; }
static void drop(T *t) { if (t) { drop(t->l); drop(t->r); free(t); } }
int main(void) { int64_t total = 0; for (int i = 0; i < 40; i++) { T *t = make(16); total += count(t); drop(t); } printf("%lld\n", (long long)total); return 0; }
