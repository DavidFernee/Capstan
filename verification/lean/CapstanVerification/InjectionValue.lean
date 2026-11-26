import Std

namespace CapstanVerification

/-!
# Value-level provenance domain

Unlike the legacy checker's monotone set of local names, this model
associates provenance with the current value stored in each local. Assignment
is a strong update: writing a clean value clears the previous value's mark.
The expression transfer is deliberately conservative and propagates provenance
through scalar computations, comparisons, aggregate construction/projection,
and control-dependent selection.

This is a formal reference domain, not yet a refinement theorem for
compiler/checker.cap. Heap aliasing and concrete AST correspondence remain
separate obligations. Aggregate construction consumes already-computed field
provenance bits; it is not a heap or alias model.
-/

/-- A local environment records provenance for the value currently in a slot. -/
abbrev ValueStore := Nat → Bool

/-- Strong update of one local; all other local facts are preserved. -/
def valueWrite (store : ValueStore) (slot : Nat) (derived : Bool) : ValueStore :=
  fun queried => if queried = slot then derived else store queried

/-- The just-written value is observable at its destination. -/
theorem valueWrite_read_same (store : ValueStore) (slot : Nat) (derived : Bool) :
    valueWrite store slot derived slot = derived := by
  simp [valueWrite]

/-- A write cannot change the provenance fact of a different local. -/
theorem valueWrite_read_other (store : ValueStore) (slot other : Nat)
    (derived : Bool) (h : other ≠ slot) :
    valueWrite store slot derived other = store other := by
  simp [valueWrite, h]

/-- Provenance-bearing expression fragment for the value-level reference semantics. -/
inductive ValueExpr where
  | literal
  | attackerInput
  | local (slot : Nat)
  | unary (value : ValueExpr)
  | binary (left right : ValueExpr)
  | compare (left right : ValueExpr)
  | convertText (value : ValueExpr)
  | join (collection separator : ValueExpr)
  | length (value : ValueExpr)
  | mapLookup (map key : ValueExpr)
  | mapMembership (map key : ValueExpr)
  | mapKeys (map : ValueExpr)
  | mapRemove (map key : ValueExpr)
  | optionalPayload (value : ValueExpr)
  | enumPayload (value : ValueExpr)
  | aggregateBuild (fieldMarks : List Bool)
  | aggregateField (aggregate : ValueExpr)
  | indexedRead (aggregate selector : ValueExpr)
  | select (condition whenTrue whenFalse : ValueExpr)
  deriving Repr

/-- Conservative dependency transfer for values and control-dependent values. -/
def valueDerived (store : ValueStore) : ValueExpr → Bool
  | .literal => false
  | .attackerInput => true
  | .local slot => store slot
  | .unary value => valueDerived store value
  | .binary left right => valueDerived store left || valueDerived store right
  | .compare left right => valueDerived store left || valueDerived store right
  | .convertText value => valueDerived store value
  | .join collection separator =>
      valueDerived store collection || valueDerived store separator
  | .length value => valueDerived store value
  | .mapLookup map key => valueDerived store map || valueDerived store key
  | .mapMembership map key => valueDerived store map || valueDerived store key
  | .mapKeys map => valueDerived store map
  | .mapRemove map key => valueDerived store map || valueDerived store key
  | .optionalPayload value => valueDerived store value
  | .enumPayload value => valueDerived store value
  | .aggregateBuild fieldMarks => fieldMarks.any id
  | .aggregateField aggregate => valueDerived store aggregate
  | .indexedRead aggregate selector =>
      valueDerived store aggregate || valueDerived store selector
  | .select condition whenTrue whenFalse =>
      valueDerived store condition || valueDerived store whenTrue ||
        valueDerived store whenFalse

/-- Assignment evaluates the RHS in the pre-state, then strongly updates its slot. -/
def valueAssign (store : ValueStore) (slot : Nat) (rhs : ValueExpr) : ValueStore :=
  valueWrite store slot (valueDerived store rhs)

/-- Clean reassignment clears stale provenance from that local. -/
theorem clean_reassignment_clears_mark (store : ValueStore) (slot : Nat)
    (hclean : valueDerived store .literal = false) :
    valueAssign store slot .literal slot = false := by
  simp [valueAssign, valueWrite, valueDerived, hclean]

/-- Attacker input assigned to a local remains marked at that local. -/
theorem attacker_assignment_marks_local (store : ValueStore) (slot : Nat) :
    valueAssign store slot .attackerInput slot = true := by
  simp [valueAssign, valueWrite, valueDerived]

/-- Assignment preserves every unrelated local's provenance fact. -/
theorem valueAssign_preserves_other (store : ValueStore) (slot other : Nat)
    (rhs : ValueExpr) (h : other ≠ slot) :
    valueAssign store slot rhs other = store other := by
  simp [valueAssign, valueWrite, h]

/-- Comparison results retain dependency on either operand. -/
theorem comparison_preserves_left (store : ValueStore) (left right : ValueExpr)
    (h : valueDerived store left = true) :
    valueDerived store (.compare left right) = true := by
  change (valueDerived store left || valueDerived store right) = true
  simp [h]

theorem comparison_preserves_right (store : ValueStore) (left right : ValueExpr)
    (h : valueDerived store right = true) :
    valueDerived store (.compare left right) = true := by
  change (valueDerived store left || valueDerived store right) = true
  simp [h]

/-- Generic text conversion and collection joining preserve provenance. -/
theorem text_conversion_preserves (store : ValueStore) (value : ValueExpr)
    (h : valueDerived store value = true) :
    valueDerived store (.convertText value) = true := by
  change valueDerived store value = true
  exact h

theorem join_preserves_collection (store : ValueStore) (collection separator : ValueExpr)
    (h : valueDerived store collection = true) :
    valueDerived store (.join collection separator) = true := by
  change (valueDerived store collection || valueDerived store separator) = true
  simp [h]

/-- Shape/length observations retain provenance. -/
theorem length_preserves (store : ValueStore) (value : ValueExpr)
    (h : valueDerived store value = true) :
    valueDerived store (.length value) = true := by
  change valueDerived store value = true
  exact h

/-- Aggregate construction is marked if any evaluated field is marked. -/
theorem aggregate_build_preserves_field (store : ValueStore)
    (fieldMarks : List Bool) (fieldMark : Bool)
    (hmem : fieldMark ∈ fieldMarks) (hderived : fieldMark = true) :
    valueDerived store (.aggregateBuild fieldMarks) = true := by
  simp [valueDerived, List.any_eq_true]
  exact ⟨fieldMark, hmem, hderived⟩

/-- A selected value is marked if its controlling condition is marked. -/
theorem selection_preserves_control (store : ValueStore)
    (condition yes no : ValueExpr)
    (h : valueDerived store condition = true) :
    valueDerived store (.select condition yes no) = true := by
  change (valueDerived store condition || valueDerived store yes ||
    valueDerived store no) = true
  simp [h]

/-- A lookup result is marked if its selector is attacker-influenced. -/
theorem map_lookup_preserves_key (store : ValueStore) (map key : ValueExpr)
    (h : valueDerived store key = true) :
    valueDerived store (.mapLookup map key) = true := by
  change (valueDerived store map || valueDerived store key) = true
  simp [h]

end CapstanVerification
