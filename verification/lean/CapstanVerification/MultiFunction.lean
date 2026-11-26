import CapstanVerification.Machine

namespace CapstanVerification

/-!
Typed function-entry and call-result contracts for the C-free multi-function
CCAM profile.

This module formalises the static argument-transfer boundary independently of
the concrete Capstan call evaluator. It does not yet prove that
verification/ccam_calls.cap implements these functions or the complete
multi-frame transition relation.
-/

/-- The CCAM register occupied by a function parameter. Parameters are the
leading registers, as required by the CCAM function contract. -/
def parameterRegisterIndex {p n : Nat} (parameterCount_le_registers : p ≤ n)
    (index : Fin p) : Fin n :=
  ⟨index.val, Nat.lt_of_lt_of_le index.isLt parameterCount_le_registers⟩

/-- A function signature relates parameter types to the leading register types. -/
structure FunctionSignature (p n : Nat) where
  parameterTypes : Fin p → Ty
  registerTypes : RegTypes n
  parameterCount_le_registers : p ≤ n
  parameters_match_registers :
    ∀ index, parameterTypes index =
      registerTypes (parameterRegisterIndex parameterCount_le_registers index)
  returnType : Option Ty

/-- Arguments supplied to a function, indexed by the exact parameter arity. -/
def ArgumentsWellTyped {p n : Nat} (signature : FunctionSignature p n)
    (arguments : Fin p → Val) : Prop :=
  ∀ index, hasType (arguments index) (signature.parameterTypes index)

/-- Initialise the callee frame: copy arguments into the leading parameter
registers and leave every local register uninitialised. -/
def initialFrameRegisters {p n : Nat}
    (_signature : FunctionSignature p n) (arguments : Fin p → Val) :
    Registers n :=
  fun register =>
    if hparameter : register.val < p then
      some (arguments ⟨register.val, hparameter⟩)
    else
      none

/-- Parameter values are copied to their corresponding leading registers. -/
theorem initialFrameRegisters_parameter_value
    {p n : Nat} (signature : FunctionSignature p n)
    (arguments : Fin p → Val) (index : Fin p) :
    initialFrameRegisters signature arguments
      (parameterRegisterIndex signature.parameterCount_le_registers index) =
      some (arguments index) := by
  unfold initialFrameRegisters parameterRegisterIndex
  simp

/-- Non-parameter registers begin uninitialised. -/
theorem initialFrameRegisters_locals_uninitialised
    {p n : Nat} (signature : FunctionSignature p n)
    (arguments : Fin p → Val) (register : Fin n)
    (hlocal : ¬ register.val < p) :
    initialFrameRegisters signature arguments register = none := by
  simp [initialFrameRegisters, hlocal]

/-- Well-typed arguments initialise a well-typed callee register file. -/
theorem initialFrameRegisters_well_typed
    {p n : Nat} (signature : FunctionSignature p n)
    (arguments : Fin p → Val)
    (harguments : ArgumentsWellTyped signature arguments) :
    WellTyped signature.registerTypes
      (initialFrameRegisters signature arguments) := by
  intro register value hread
  by_cases hparameter : register.val < p
  · have hvalue :
        arguments ⟨register.val, hparameter⟩ = value := by
      simpa [initialFrameRegisters, hparameter] using hread
    subst value
    let index : Fin p := ⟨register.val, hparameter⟩
    have htyped := harguments index
    have hindex :
        parameterRegisterIndex signature.parameterCount_le_registers index =
          register := by
      apply Fin.ext
      rfl
    rw [signature.parameters_match_registers index, hindex] at htyped
    exact htyped
  · simp [initialFrameRegisters, hparameter] at hread

/-- A non-void call destination must have exactly the callee's result type.
Void calls have no destination; no other pairing is admitted. -/
def ReturnDestinationMatches {n : Nat}
    (callerTypes : RegTypes n) (returnType : Option Ty)
    (destination : Option (Fin n)) : Prop :=
  match returnType, destination with
  | none, none => True
  | some resultType, some register => callerTypes register = resultType
  | _, _ => False

/-- A valid non-void return destination preserves the exact result type. -/
theorem return_destination_has_exact_type
    {n : Nat} (callerTypes : RegTypes n) (resultType : Ty)
    (destination : Fin n)
    (hmatch : ReturnDestinationMatches callerTypes (some resultType)
      (some destination)) :
    callerTypes destination = resultType := by
  exact hmatch

/-- A void return cannot write a caller destination. -/
theorem void_return_has_no_destination
    {n : Nat} (callerTypes : RegTypes n) (destination : Fin n)
    (hmatch : ReturnDestinationMatches callerTypes none
      (some destination)) : False := by
  exact hmatch

/-- A non-void return cannot silently discard its result in this profile. -/
theorem nonvoid_return_requires_destination
    {n : Nat} (callerTypes : RegTypes n) (resultType : Ty)
    (hmatch : ReturnDestinationMatches callerTypes (some resultType) none) :
    False := by
  exact hmatch

/-- A call frame carries a proof that every initialized local agrees with its
function's declared register signature. -/
structure TypedCallFrame (p n : Nat) where
  signature : FunctionSignature p n
  registers : Registers n
  registers_well_typed :
    WellTyped signature.registerTypes registers

/-- Construct a callee frame from arguments already checked against its
parameter signature. All non-parameter registers are uninitialised. -/
def enterTypedFunction {p n : Nat}
    (signature : FunctionSignature p n) (arguments : Fin p → Val)
    (harguments : ArgumentsWellTyped signature arguments) :
    TypedCallFrame p n :=
  { signature := signature
    registers := initialFrameRegisters signature arguments
    registers_well_typed :=
      initialFrameRegisters_well_typed signature arguments harguments }

/-- The frame constructor preserves the exact declared function signature. -/
theorem enterTypedFunction_signature {p n : Nat}
    (signature : FunctionSignature p n) (arguments : Fin p → Val)
    (harguments : ArgumentsWellTyped signature arguments) :
    (enterTypedFunction signature arguments harguments).signature = signature :=
  rfl

/-- A returned value is admitted only when it has the callee's declared type.
Void is represented by the absence of a value. -/
def ReturnValueMatches (returnType : Option Ty) (value : Option Val) : Prop :=
  match returnType, value with
  | none, none => True
  | some expected, some actual => hasType actual expected
  | _, _ => False

/-- Every non-void return payload has exactly the declared source type. -/
theorem returned_value_has_declared_type
    (returnType : Ty) (value : Val)
    (hreturn : ReturnValueMatches (some returnType) (some value)) :
    hasType value returnType :=
  hreturn

/-- A void function cannot return an observable value. -/
theorem void_function_returns_no_value
    (value : Val)
    (hreturn : ReturnValueMatches none (some value)) :
    False :=
  hreturn

/-- A non-void function cannot complete without a return value. -/
theorem nonvoid_function_requires_value
    (returnType : Ty)
    (hreturn : ReturnValueMatches (some returnType) none) :
    False :=
  hreturn

end CapstanVerification


namespace CapstanVerification


/-- Commit a non-void callee result into the caller's statically typed
destination. The caller's register invariant is preserved because the
callee's return contract and the call-site destination contract agree on the
same exact type. This theorem is the typed core of the concrete evaluator's
preflight-then-write return path. -/
theorem return_write_preserves_caller_well_typed
    {n : Nat} (callerTypes : RegTypes n) (callerRegisters : Registers n)
    (hcaller : WellTyped callerTypes callerRegisters)
    (resultType : Ty) (destination : Fin n) (value : Val)
    (hreturn : ReturnValueMatches (some resultType) (some value))
    (hdestination : ReturnDestinationMatches callerTypes
      (some resultType) (some destination)) :
    WellTyped callerTypes (write callerRegisters destination value) := by
  have hvalue : hasType value resultType :=
    returned_value_has_declared_type resultType value hreturn
  have hdestinationType : callerTypes destination = resultType :=
    return_destination_has_exact_type callerTypes resultType destination
      hdestination
  have hcallerValue : hasType value (callerTypes destination) := by
    simpa [hdestinationType] using hvalue
  exact write_preserves_well_typed hcaller destination value hcallerValue


end CapstanVerification
