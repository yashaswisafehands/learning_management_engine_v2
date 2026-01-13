# from neomodel import (BooleanProperty, DateTimeProperty, FloatProperty,
#                       IntegerProperty, RelationshipFrom, RelationshipTo,
#                       StringProperty, StructuredNode, StructuredRel,
#                       UniqueIdProperty)


# class CertificateModuleRel(StructuredRel):
#     """Relationship model capturing module-level settings within a certificate profile version."""

#     weightage = FloatProperty(default=1.0)
#     passing_percentage = FloatProperty(default=75.0)

#     # Whether this module is mandatory to qualify for the champion certificate
#     mandatory = BooleanProperty(default=False)

#     # Optional ordering for presentation
#     order = IntegerProperty()


# class CertificateProfile(StructuredNode):
#     """Country-specific certificate profile container.

#     Each country has a single CertificateProfile node identified by a unique country_code.
#     Versioned content and configuration live on CertificateProfileVersion nodes.
#     """

#     certificate_profile_id = UniqueIdProperty()

#     # Country identity
#     country_code = StringProperty(required=True, unique_index=True)
#     country_name = StringProperty()
#     slug = StringProperty(required=True, unique_index=True)  # crt-country_code
#     current_version = StringProperty()  # certificate_template-country_code-version
#     is_deleted = BooleanProperty(default=False)

#     # Current pointer to the active version
#     current_version_rel = RelationshipTo("CertificateProfileVersion", "CURRENT_VERSION")

#     certificate_template = StringProperty()  # CNE , CPN , RN , RM etc.

#     # All versions
#     versions = RelationshipTo("CertificateProfileVersion", "HAS_VERSION")

#     created_at = DateTimeProperty(default_now=True)
#     created_by = StringProperty(default="System")


# class CertificateProfileVersion(StructuredNode):
#     """Versioned certificate profile configuration for a country.

#     Stores language associations and per-module configuration such as weightage,
#     passing percentage, and whether a module is mandatory for the champion certificate.
#     """

#     certificate_profile_version_id = UniqueIdProperty()
#     version = FloatProperty(default=1.0)
#     version_code = StringProperty(
#         required=True, unique_index=True
#     )  # certificate_template-country_code-version
#     status = StringProperty(
#         required=True,
#         index=True,
#         choices={
#             "draft": "draft",
#             "active": "active",
#             "superseded": "superseded",
#             "reverted": "reverted",
#             "archived": "archived",
#             "review": "review",
#         },
#     )

#     region = StringProperty(index=True)
#     country_code = StringProperty(index=True)
#     certificate_template = StringProperty()

#     # Display/metadata
#     nursing_council_name = StringProperty()
#     # Score required to obtain the champion certificate (profile-level threshold)
#     champion_certificate_score = FloatProperty(default=0.0)

#     # Associations
#     certificate_profile = RelationshipFrom(CertificateProfile, "HAS_VERSION")

#     # Link modules with per-module configuration captured on the relationship
#     modules = RelationshipTo(
#         "app.models.modules.Module", "INCLUDES_MODULE", model=CertificateModuleRel
#     )

#     created_at = DateTimeProperty(default_now=True)
#     created_by = StringProperty(default="System")
#     is_deleted = BooleanProperty(default=False)



from neomodel import (BooleanProperty, DateTimeProperty, FloatProperty,
                      IntegerProperty, RelationshipFrom, RelationshipTo,
                      StringProperty, StructuredNode, StructuredRel,
                      UniqueIdProperty)
class CertificateModuleRel(StructuredRel):
    """Relationship model capturing module-level settings within a certificate profile version."""
    weightage = FloatProperty(default=1.0)
    passing_percentage = FloatProperty(default=75.0)
    # Whether this module is mandatory to qualify for the champion certificate
    mandatory = BooleanProperty(default=False)
    # Optional ordering for presentation
    order = IntegerProperty()
class CertificateProfile(StructuredNode):
    """Country-specific certificate profile container.
    Each country has a single CertificateProfile node identified by a unique country_code.
    Versioned content and configuration live on CertificateProfileVersion nodes.
    """
    certificate_profile_id = UniqueIdProperty()
    # Country identity
    country_code = StringProperty(required=True, unique_index=True)
    country_name = StringProperty()
    slug = StringProperty(required=True, unique_index=True)  # crt-country_code
    current_version = StringProperty()  # certificate_template-country_code-version
    is_deleted = BooleanProperty(default=False)
    # Current pointer to the active version
    current_version_rel = RelationshipTo("CertificateProfileVersion", "CURRENT_VERSION")
    certificate_template = StringProperty()  # CNE , CPN , RN , RM etc.
    templates = RelationshipTo("app.models.assets.Asset", "USES_ASSET")
    # All versions
    versions = RelationshipTo("CertificateProfileVersion", "HAS_VERSION")
    created_at = DateTimeProperty(default_now=True)
    created_by = StringProperty(default="System")
class CertificateProfileVersion(StructuredNode):
    """Versioned certificate profile configuration for a country.
    Stores language associations and per-module configuration such as weightage,
    passing percentage, and whether a module is mandatory for the champion certificate.
    """
    certificate_profile_version_id = UniqueIdProperty()
    version = FloatProperty(default=1.0)
    version_code = StringProperty(
        required=True, unique_index=True
    )  # certificate_template-country_code-version
    status = StringProperty(
        required=True,
        index=True,
        choices={
            "draft": "draft",
            "active": "active",
            "superseded": "superseded",
            "reverted": "reverted",
            "archived": "archived",
            "review": "review",
        },
    )
    region = StringProperty(index=True)
    country_code = StringProperty(index=True)
    certificate_template = StringProperty()
    templates = RelationshipTo("app.models.assets.Asset", "USES_ASSET")
    # Display/metadata
    nursing_council_name = StringProperty()
    # Score required to obtain the champion certificate (profile-level threshold)
    champion_certificate_score = FloatProperty(default=0.0)
    # Associations
    certificate_profile = RelationshipFrom(CertificateProfile, "HAS_VERSION")
    # Link modules with per-module configuration captured on the relationship
    modules = RelationshipTo(
        "app.models.modules.Module", "INCLUDES_MODULE", model=CertificateModuleRel
    )
    created_at = DateTimeProperty(default_now=True)
    created_by = StringProperty(default="System")
    is_deleted = BooleanProperty(default=False)
