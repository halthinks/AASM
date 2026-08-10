from aasm import CertificateRecord, DecisionLiteral, ProjectionCertificateVerifier, projection_payload


constraint = {
    "constraint_id": "LC-example",
    "body": [DecisionLiteral("method", "EQ", "A").to_dict()],
    "guard": {"const": True},
    "source_conflict_id": "C-example",
    "source_explanation_id": "X-example",
    "evidence_ids": ["E-example"],
    "scope": {},
}
certificate = CertificateRecord(
    "CERT-example",
    "PROJECTION",
    "LEARNED_CONSTRAINT",
    constraint["constraint_id"],
    projection_payload(constraint),
    "aasm.projection",
)
verification = ProjectionCertificateVerifier().verify(certificate, constraint)
print(verification.to_dict())
