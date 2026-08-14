-------------------------- MODULE AASMCrossRunKnowledge --------------------------
EXTENDS Naturals

VARIABLES envelope_received,
          admission_validated,
          admission_authorized,
          foreign_authority_inherited,
          materialized,
          reuse_enabled,
          source_revoked,
          materialized_active,
          privacy_compatible,
          reputation_recorded,
          reputation_granted_authority,
          reputation_granted_resources

vars == <<envelope_received, admission_validated, admission_authorized,
          foreign_authority_inherited, materialized, reuse_enabled,
          source_revoked, materialized_active, privacy_compatible,
          reputation_recorded, reputation_granted_authority,
          reputation_granted_resources>>

Init ==
  /\ envelope_received = FALSE
  /\ admission_validated = FALSE
  /\ admission_authorized = FALSE
  /\ foreign_authority_inherited = FALSE
  /\ materialized = FALSE
  /\ reuse_enabled = FALSE
  /\ source_revoked = FALSE
  /\ materialized_active = FALSE
  /\ privacy_compatible = TRUE
  /\ reputation_recorded = FALSE
  /\ reputation_granted_authority = FALSE
  /\ reputation_granted_resources = FALSE

ReceiveEnvelope ==
  /\ ~envelope_received
  /\ envelope_received' = TRUE
  /\ UNCHANGED <<admission_validated, admission_authorized,
                  foreign_authority_inherited, materialized, reuse_enabled,
                  source_revoked, materialized_active, privacy_compatible,
                  reputation_recorded, reputation_granted_authority,
                  reputation_granted_resources>>

ValidateAdmission ==
  /\ envelope_received
  /\ privacy_compatible
  /\ ~admission_validated
  /\ admission_validated' = TRUE
  /\ UNCHANGED <<envelope_received, admission_authorized,
                  foreign_authority_inherited, materialized, reuse_enabled,
                  source_revoked, materialized_active, privacy_compatible,
                  reputation_recorded, reputation_granted_authority,
                  reputation_granted_resources>>

AuthorizeAdmission ==
  /\ admission_validated
  /\ ~admission_authorized
  /\ admission_authorized' = TRUE
  /\ UNCHANGED <<envelope_received, admission_validated,
                  foreign_authority_inherited, materialized, reuse_enabled,
                  source_revoked, materialized_active, privacy_compatible,
                  reputation_recorded, reputation_granted_authority,
                  reputation_granted_resources>>

Materialize ==
  /\ admission_authorized
  /\ ~source_revoked
  /\ ~materialized
  /\ materialized' = TRUE
  /\ materialized_active' = TRUE
  /\ UNCHANGED <<envelope_received, admission_validated, admission_authorized,
                  foreign_authority_inherited, reuse_enabled, source_revoked,
                  privacy_compatible, reputation_recorded,
                  reputation_granted_authority, reputation_granted_resources>>

EnableReuse ==
  /\ admission_authorized
  /\ ~source_revoked
  /\ ~reuse_enabled
  /\ reuse_enabled' = TRUE
  /\ UNCHANGED <<envelope_received, admission_validated, admission_authorized,
                  foreign_authority_inherited, materialized, source_revoked,
                  materialized_active, privacy_compatible, reputation_recorded,
                  reputation_granted_authority, reputation_granted_resources>>

RevokeSource ==
  /\ admission_authorized
  /\ ~source_revoked
  /\ source_revoked' = TRUE
  /\ reuse_enabled' = FALSE
  /\ materialized_active' = FALSE
  /\ UNCHANGED <<envelope_received, admission_validated, admission_authorized,
                  foreign_authority_inherited, materialized,
                  privacy_compatible, reputation_recorded,
                  reputation_granted_authority, reputation_granted_resources>>

RecordReputation ==
  /\ admission_authorized
  /\ ~source_revoked
  /\ ~reputation_recorded
  /\ reputation_recorded' = TRUE
  /\ reputation_granted_authority' = FALSE
  /\ reputation_granted_resources' = FALSE
  /\ UNCHANGED <<envelope_received, admission_validated, admission_authorized,
                  foreign_authority_inherited, materialized, reuse_enabled,
                  source_revoked, materialized_active, privacy_compatible>>

AttemptPrivacyLeak ==
  /\ ~privacy_compatible
  /\ UNCHANGED vars

Quiesce == UNCHANGED vars

Next == ReceiveEnvelope
     \/ ValidateAdmission
     \/ AuthorizeAdmission
     \/ Materialize
     \/ EnableReuse
     \/ RevokeSource
     \/ RecordReputation
     \/ AttemptPrivacyLeak
     \/ Quiesce

ForeignAuthorityNeverInherited == ~foreign_authority_inherited
AdmissionRequiredBeforeMaterialization == materialized => admission_authorized
AdmissionRequiredBeforeReuse == reuse_enabled => admission_authorized
RevocationBlocksReuse == source_revoked => ~reuse_enabled
RevocationInvalidatesMaterializedMemory == source_revoked => ~materialized_active
PrivateKnowledgeNeverLeaksAcrossPrincipal == ~privacy_compatible => ~admission_validated
ReputationNeverGrantsAuthority == ~reputation_granted_authority
ReputationNeverGrantsResourceEntitlement == ~reputation_granted_resources

Spec == Init /\ [][Next]_vars

=============================================================================
