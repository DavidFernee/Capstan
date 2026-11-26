import Lake
open Lake DSL

package capstan_verification where
  version := v!"0.1.0"
  defaultTargets := #[`CapstanVerification]

lean_lib CapstanVerification where
  srcDir := "."
  roots := #[`CapstanVerification, `NativeMemoryLifecycle, `NativeReachability,
    `NativeHandleReachability, `NativeBoundedMarker]
