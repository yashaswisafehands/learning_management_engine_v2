from typing import List, Optional

from neomodel import db
from neomodel.exceptions import DoesNotExist

from app.models.certificate_profiles import (CertificateProfile,
                                             CertificateProfileVersion)
from app.models.modules import Module
from app.schemas.certificate_profiles import (CertificateProfileCreateRequest,
                                              CertificateProfileUpdateRequest)
from app.utils.version_utils import increment_version


class CertificateProfileRepository:
    @staticmethod
    def create_profile(data: CertificateProfileCreateRequest) -> CertificateProfile:
        # Enforce uniqueness by slug derived from country_code
        slug = f"crt-{data.country_code}".lower()

        existing = CertificateProfile.nodes.filter(slug=slug)
        if existing:
            raise ValueError(f"Certificate profile with slug '{slug}' already exists")

        # Create the parent profile node
        profile = CertificateProfile(
            slug=slug,
            country_code=data.country_code.lower(),  # normalize country_code as well
            country_name=data.country_name,
            certificate_template=(
                data.certificate_template or ""
            ).upper(),  # keep template consistent (optional)
            is_deleted=False,
        ).save()

        # Create initial draft version 1.0 for the new profile
        version_code = f"{(data.certificate_template or '').upper()}-{data.country_code.lower()}-1.0"
        version = CertificateProfileVersion(
            version=1.0,
            status="draft",
            version_code=version_code,
            country_code=data.country_code.lower(),
            region=None,
            nursing_council_name=data.nursing_council_name,
            champion_certificate_score=(data.champion_certificate_score or 0.0),
            created_by="System",
            certificate_template=(data.certificate_template or "").upper(),
        ).save()

        # Link modules with relationship properties, honoring provided order or defaulting to index+1
        for idx, module_config in enumerate(getattr(data, "modules", []) or []):
            try:
                module = Module.nodes.get(module_id=module_config.module_id)
            except Module.DoesNotExist:  # type: ignore[attr-defined]
                raise ValueError(
                    f"Module with ID '{module_config.module_id}' does not exist"
                )
            rel_payload = {
                "weightage": module_config.weightage,
                "passing_percentage": module_config.passing_percentage,
                "mandatory": module_config.mandatory,
            }
            order_value = (
                module_config.order if module_config.order is not None else idx + 1
            )
            rel_payload["order"] = order_value
            version.modules.connect(module, rel_payload)

        # Connect version to profile (HAS_VERSION)
        profile.versions.connect(version)
        profile.save()
        return profile

    @staticmethod
    def get_by_id(profile_id: str) -> CertificateProfile:
        try:
            return CertificateProfile.nodes.get(certificate_profile_id=profile_id)
        except DoesNotExist:
            raise ValueError(f"Certificate profile '{profile_id}' not found")

    @staticmethod
    def get_by_country_code(country_code: str) -> CertificateProfile:
        profiles = CertificateProfile.nodes.filter(country_code=country_code)
        if not profiles:
            raise ValueError(
                f"Certificate profile with country_code '{country_code}' not found"
            )
        # unique by design
        return profiles[0]

    @staticmethod
    def list_profiles() -> List[CertificateProfile]:
        return list(CertificateProfile.nodes.filter(is_deleted=False))

    @staticmethod
    def get_profiles(status: str = "active", include_versions: bool = False) -> List:
        """Return profiles or profile versions depending on include_versions.

        - include_versions=True and status=active -> profiles that have an active CURRENT_VERSION
        - include_versions=True and status=all -> all profiles
        - include_versions=False and status=active -> list of active versions (via CURRENT_VERSION)
        - include_versions=False and status=all -> one representative version per profile (latest by numeric version)
        """
        from neomodel import db

        if include_versions:
            if status == "active":
                query = """
                    MATCH (p:CertificateProfile)-[:CURRENT_VERSION]->(v:CertificateProfileVersion {status:'active'})
                    RETURN DISTINCT p
                """
                rows, _ = db.cypher_query(query)
                return [CertificateProfile.inflate(r[0]) for r in rows]
            else:
                return list(CertificateProfile.nodes.filter(is_deleted=False))
        else:
            if status == "active":
                query = """
                    MATCH (p:CertificateProfile)-[:CURRENT_VERSION]->(v:CertificateProfileVersion {status:'active'})
                    RETURN v
                """
                rows, _ = db.cypher_query(query)
                return [CertificateProfileVersion.inflate(r[0]) for r in rows]
            else:
                # For each profile, pick latest version by number if present
                profiles = list(CertificateProfile.nodes.filter(is_deleted=False))
                result: list[CertificateProfileVersion] = []
                for p in profiles:
                    versions = p.versions.all()
                    if versions:
                        latest = max(versions, key=lambda v: getattr(v, "version", 0))
                        result.append(latest)
                return result

    @staticmethod
    def get_profile_and_versions_by_country_code(
        country_code: str, status: str = "active"
    ) -> CertificateProfile:
        """Return the CertificateProfile filtered by country_code.

        If status='active', callers may choose to consider only active versions on the consumer side.
        """
        profiles = CertificateProfile.nodes.filter(country_code=country_code)
        if not profiles:
            raise ValueError(
                f"Certificate profile with country_code '{country_code}' not found"
            )
        return profiles[0]

    @staticmethod
    def _get_by_slug(slug: str) -> Optional[CertificateProfile]:
        profiles = CertificateProfile.nodes.filter(slug=slug)
        return profiles[0] if profiles else None

    @staticmethod
    def _compute_next_version(profile: CertificateProfile) -> float:
        versions = profile.versions.all()
        if not versions:
            return 1.0
        latest = max(versions, key=lambda v: getattr(v, "version", 0.0))
        return increment_version(getattr(latest, "version", 1.0))

    @staticmethod
    def _get_latest_version(
        profile: CertificateProfile,
    ) -> Optional[CertificateProfileVersion]:
        versions = profile.versions.all()
        if not versions:
            return None
        return max(versions, key=lambda v: getattr(v, "version", 0.0))

    @staticmethod
    def create_version(
        profile_id: str, data: CertificateProfileUpdateRequest
    ) -> CertificateProfileVersion:
        profile = CertificateProfileRepository.get_by_id(profile_id)
        latest_version = CertificateProfileRepository._get_latest_version(profile)
        try:
            current_version = profile.current_version_rel.single()
        except Exception:
            current_version = None

        source_version = current_version or latest_version
        new_version_number = CertificateProfileRepository._compute_next_version(profile)

        if data.country_name is not None:
            profile.country_name = data.country_name
        if data.certificate_template is not None:
            profile.certificate_template = data.certificate_template

        nursing_council_name = (
            data.nursing_council_name
            if data.nursing_council_name is not None
            else getattr(source_version, "nursing_council_name", None)
        )
        champion_certificate_score = (
            data.champion_certificate_score
            if data.champion_certificate_score is not None
            else getattr(source_version, "champion_certificate_score", 0.0)
        )
        region = (
            data.region
            if data.region is not None
            else getattr(source_version, "region", None)
        )
        created_by = (
            data.created_by
            if data.created_by is not None
            else getattr(source_version, "created_by", "System")
        )

        template = profile.certificate_template
        if not template:
            raise ValueError(
                "Certificate template is required to create a profile version"
            )

        version = CertificateProfileVersion(
            version=new_version_number,
            status="draft",
            version_code=f"{template}-{profile.country_code}-{new_version_number}",
            country_code=profile.country_code,
            region=region,
            nursing_council_name=nursing_council_name,
            champion_certificate_score=champion_certificate_score,
            created_by=created_by or "System",
            certificate_template=template,
        ).save()

        # Link modules with relationship properties
        modules_payload = data.modules
        if modules_payload is None and source_version:
            try:
                existing_modules = source_version.modules.all()
            except Exception:
                existing_modules = []
            for module in existing_modules:
                rel = source_version.modules.relationship(module)
                rel_payload = {
                    "weightage": getattr(rel, "weightage", 0.0),
                    "passing_percentage": getattr(rel, "passing_percentage", 0.0),
                    "mandatory": getattr(rel, "mandatory", False),
                }
                order_value = getattr(rel, "order", None)
                if order_value is not None:
                    rel_payload["order"] = order_value
                version.modules.connect(module, rel_payload)
        else:
            for idx, module_config in enumerate(modules_payload or []):
                try:
                    module = Module.nodes.get(module_id=module_config.module_id)
                except Module.DoesNotExist:  # type: ignore[attr-defined]
                    raise ValueError(
                        f"Module with ID '{module_config.module_id}' does not exist"
                    )
                rel_payload = {
                    "weightage": module_config.weightage,
                    "passing_percentage": module_config.passing_percentage,
                    "mandatory": module_config.mandatory,
                }
                order_value = (
                    module_config.order if module_config.order is not None else idx + 1
                )
                rel_payload["order"] = order_value
                version.modules.connect(module, rel_payload)

        profile.versions.connect(version)
        profile.save()
        return version

    @staticmethod
    def update_version_status(
        version_id: str, status: str, updated_by: Optional[str] = "System"
    ) -> CertificateProfileVersion:
        try:
            version = CertificateProfileVersion.nodes.get(
                certificate_profile_version_id=version_id
            )
        except CertificateProfileVersion.DoesNotExist:  # type: ignore[attr-defined]
            raise ValueError(f"Certificate profile version '{version_id}' not found")

        valid = {"draft", "active", "superseded", "reverted", "archived", "review"}
        if status not in valid:
            raise ValueError(
                f"Invalid status '{status}'. Must be one of: {', '.join(sorted(valid))}"
            )

        # Determine parent profile
        rows, _ = db.cypher_query(
            """
        MATCH (p:CertificateProfile)-[:HAS_VERSION]->
            (v:CertificateProfileVersion {certificate_profile_version_id:$vid})
            RETURN p LIMIT 1
            """,
            {"vid": version_id},
        )
        parent = CertificateProfile.inflate(rows[0][0]) if rows else None

        version.status = status
        version.created_by = updated_by or version.created_by
        version.save()

        # If activating, mark other active versions as superseded/reverted based on version number
        if parent and status == "active":
            for other in parent.versions.all():
                if other.certificate_profile_version_id == version_id:
                    continue
                if getattr(other, "status", None) == "active":
                    if getattr(version, "version", 0) > getattr(other, "version", 0):
                        other.status = "superseded"
                    elif getattr(version, "version", 0) < getattr(other, "version", 0):
                        other.status = "reverted"
                    other.save()

            # Update current version linkage and string identifier
            try:
                existing = parent.current_version_rel.single()
                if existing:
                    parent.current_version_rel.disconnect(existing)
            except Exception:
                existing = None
            parent.current_version_rel.connect(version)
            parent.current_version = getattr(version, "version_code", None)
            parent.save()

        elif parent and status != "active":
            # If version being updated was the current pointer, clear pointer
            try:
                current = parent.current_version_rel.single()
            except Exception:
                current = None
            if current and current.certificate_profile_version_id == version_id:
                parent.current_version_rel.disconnect(current)
                parent.current_version = None
                parent.save()

        return version
