{-# OPTIONS --safe --without-K #-}
module RuntimeGuardTraceCorrespondence where
open import Agda.Builtin.Equality using (_≡_; refl)
open import RuntimeCriticalGuardTraceModel using (runtimeCriticalGuardTrace)
open import PythonRuntimeGuardTraceGenerated using (pythonRuntimeGuardTrace)
runtime-critical-guard-trace-refines-exact-python-runtime :
  runtimeCriticalGuardTrace ≡ pythonRuntimeGuardTrace
runtime-critical-guard-trace-refines-exact-python-runtime = refl
