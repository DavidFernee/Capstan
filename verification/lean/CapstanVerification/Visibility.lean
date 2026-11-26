import Std

namespace CapstanVerification

/-!
A small formal judgement for the module-identity boundary introduced by
Capstan's private struct fields and opaque structs.

This models the policy only. It does not yet extract or verify the production
Capstan checker, parser, import loader, AST source identities, or diagnostics.
In particular, this file must not be cited as a proof that compiler code
implements the judgement.
-/

abbrev ModuleId := Nat

inductive FieldOperation where
  | read
  | write
  | initialise
  deriving DecidableEq, Repr

structure FieldDeclaration where
  ownerModule : ModuleId
  explicitlyPrivate : Bool
  opaqueType : Bool
  deriving DecidableEq, Repr

/-- A field is hidden if its declaration is private or its containing type is opaque. -/
def fieldIsHidden (field : FieldDeclaration) : Bool :=
  field.explicitlyPrivate || field.opaqueType

/-- The policy judgement for reading, writing, or initialising a field. -/
def permitsFieldOperation (currentModule : ModuleId)
    (field : FieldDeclaration) (_operation : FieldOperation) : Bool :=
  !(fieldIsHidden field) || currentModule == field.ownerModule

/-- Opaque values may only be constructed by code in their defining module. -/
def permitsOpaqueConstruction (currentModule ownerModule : ModuleId)
    (opaqueType : Bool) : Bool :=
  !opaqueType || currentModule == ownerModule

/-- The operation kind does not weaken the field-visibility boundary. -/
theorem field_operation_same_policy (module : ModuleId)
    (field : FieldDeclaration) :
    permitsFieldOperation module field .read =
    permitsFieldOperation module field .write ∧
    permitsFieldOperation module field .write =
    permitsFieldOperation module field .initialise := by
  constructor <;> rfl

/-- A private field is inaccessible from a different defining module. -/
theorem private_field_denied_cross_module
    (currentModule : ModuleId) (field : FieldDeclaration)
    (hPrivate : field.explicitlyPrivate = true)
    (hDifferent : currentModule ≠ field.ownerModule) :
    permitsFieldOperation currentModule field .read = false := by
  simp [permitsFieldOperation, fieldIsHidden, hPrivate, hDifferent]

/-- Every field of an opaque type is inaccessible from another module. -/
theorem opaque_field_denied_cross_module
    (currentModule : ModuleId) (field : FieldDeclaration)
    (hOpaque : field.opaqueType = true)
    (hDifferent : currentModule ≠ field.ownerModule) :
    permitsFieldOperation currentModule field .write = false := by
  simp [permitsFieldOperation, fieldIsHidden, hOpaque, hDifferent]

/-- Public, non-opaque fields remain accessible across module boundaries. -/
theorem public_field_permitted_cross_module
    (currentModule : ModuleId) (field : FieldDeclaration)
    (hPublic : field.explicitlyPrivate = false)
    (hNonOpaque : field.opaqueType = false) :
    permitsFieldOperation currentModule field .read = true := by
  simp [permitsFieldOperation, fieldIsHidden, hPublic, hNonOpaque]

/-- The defining module retains access to its own private representation. -/
theorem owner_can_access_private_field
    (module : ModuleId) (field : FieldDeclaration)
    (hOwner : module = field.ownerModule) :
    permitsFieldOperation module field .read = true := by
  simp [permitsFieldOperation, hOwner]

/-- An importer cannot construct an opaque value, regardless of its fields. -/
theorem opaque_construction_denied_cross_module
    (currentModule ownerModule : ModuleId) (opaqueType : Bool)
    (hOpaque : opaqueType = true)
    (hDifferent : currentModule ≠ ownerModule) :
    permitsOpaqueConstruction currentModule ownerModule opaqueType = false := by
  simp [permitsOpaqueConstruction, hOpaque, hDifferent]

/-- The defining module can construct its own opaque value. -/
theorem opaque_construction_permitted_owner
    (module : ModuleId) :
    permitsOpaqueConstruction module module true = true := by
  simp [permitsOpaqueConstruction]

/-! These examples are kernel-checked decision instances for the policy table. -/

example : permitsFieldOperation 2
    { ownerModule := 1,
      explicitlyPrivate := true, opaqueType := false } .read = false := by
  decide

example : permitsFieldOperation 2
    { ownerModule := 1
      explicitlyPrivate := false, opaqueType := true } .initialise = false := by
  decide

example : permitsFieldOperation 2
    { ownerModule := 1, explicitlyPrivate := false,
      opaqueType := false } .write = true := by
  decide

example : permitsOpaqueConstruction 2 1 true = false := by
  decide

end CapstanVerification
