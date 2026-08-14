bool envelope_received = false;
bool admission_validated = false;
bool admission_authorized = false;
bool foreign_authority_inherited = false;
bool materialized = false;
bool reuse_enabled = false;
bool source_revoked = false;
bool materialized_active = false;
bool privacy_compatible = true;
bool reputation_recorded = false;
bool reputation_granted_authority = false;
bool reputation_granted_resources = false;

active proctype CrossRunKnowledge() {
    envelope_received = true;
    if
    :: privacy_compatible -> admission_validated = true
    :: else -> skip
    fi;
    if
    :: admission_validated -> admission_authorized = true
    :: else -> skip
    fi;
    if
    :: admission_authorized ->
        if
        :: materialized = true; materialized_active = true
        :: reuse_enabled = true
        :: reputation_recorded = true
        fi
    :: else -> skip
    fi;
    if
    :: admission_authorized -> source_revoked = true; reuse_enabled = false; materialized_active = false
    :: else -> skip
    fi;
    assert(!foreign_authority_inherited);
    assert(!materialized || admission_authorized);
    assert(!reuse_enabled || admission_authorized);
    assert(!source_revoked || !reuse_enabled);
    assert(!source_revoked || !materialized_active);
    assert(privacy_compatible || !admission_validated);
    assert(!reputation_granted_authority);
    assert(!reputation_granted_resources)
}
