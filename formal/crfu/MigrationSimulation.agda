{-# OPTIONS --safe --without-K #-}
module MigrationSimulation where

open import Agda.Builtin.String using (String)

-- Version identities are explicit data, while invariant preservation is a
-- proposition supplied as a proof term rather than an unchecked Boolean.
record MigrationSimulation (Source Target : Set) : Set₁ where
  constructor migrationSimulation
  field
    sourceVersion : String
    sourceArtifactDigest : String
    targetVersion : String
    targetArtifactDigest : String
    SourceInvariant : Source -> Set
    TargetInvariant : Target -> Set
    migrate : Source -> Target
    invariantSimulation :
      (source : Source) -> SourceInvariant source ->
      TargetInvariant (migrate source)
open MigrationSimulation

-- Any valid migration simulation transports only the stated invariant.
-- This theorem cannot transfer binary identity, authorization, signatures,
-- or certification: none of those properties occurs in TargetInvariant.
migration-preserves-declared-invariant :
  {Source Target : Set} ->
  (m : MigrationSimulation Source Target) ->
  (source : Source) -> SourceInvariant m source ->
  TargetInvariant m (migrate m source)
migration-preserves-declared-invariant m source proof =
  invariantSimulation m source proof

-- A valid migration object binds both endpoints and the proof to one
-- deterministic transformation; an empty digest is not a real digest policy
-- and must be rejected by the external source-binding validator.
migration-source-destination-versions-are-explicit :
  {Source Target : Set} -> (m : MigrationSimulation Source Target) ->
  String
migration-source-destination-versions-are-explicit m = sourceVersion m
