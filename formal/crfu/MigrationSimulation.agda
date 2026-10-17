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

-- Endpoint metadata is returned as one record so downstream evidence
-- cannot accidentally consume only the source version while ignoring the target.
-- This record exposes lineage data; it does not itself validate digest syntax or
-- prove that external bytes match the declared digests. The trusted source-binding
-- validator remains responsible for those checks.
record MigrationEndpoints : Set where
  constructor migrationEndpoints
  field
    endpointSourceVersion : String
    endpointSourceDigest : String
    endpointTargetVersion : String
    endpointTargetDigest : String
open MigrationEndpoints

-- A valid migration object binds both versions and both artifact digests.
migration-source-destination-versions-are-explicit :
  {Source Target : Set} -> (m : MigrationSimulation Source Target) ->
  MigrationEndpoints
migration-source-destination-versions-are-explicit m =
  migrationEndpoints
    (sourceVersion m)
    (sourceArtifactDigest m)
    (targetVersion m)
    (targetArtifactDigest m)
