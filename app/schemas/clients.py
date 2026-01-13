# from typing import Any, List, Optional, Union

# from pydantic import BaseModel
# from app.schemas.key_learning_points import KeyLearningPointResponse

# class ManifestResourceRef(BaseModel):
#     resource_id: str
#     slug: Optional[str] = None
#     title: Optional[str] = None
#     description: Optional[str] = None
#     version: Optional[float] = None
#     order: Optional[int] = None
#     content: Optional[str] = None
#     icon: Optional[str] = None


# class ManifestModule(BaseModel):
#     module_id: str
#     slug: Optional[str] = None
#     title: Optional[str] = None
#     description: Optional[str] = None
#     version: Optional[float] = None
#     status: Optional[str] = None
#     icon: Optional[str] = None
#     asset_total_size_bytes: int = 0
#     asset_filenames: List[str] = []
#     videos: List[ManifestResourceRef] = []
#     action_cards: List[ManifestResourceRef] = []
#     practical_procedures: List[ManifestResourceRef] = []
#     drugs: List[ManifestResourceRef] = []
#     keylearning_points: List[KeyLearningPointResponse] = []


# class ManifestTranscription(BaseModel):
#     """Flattened transcription for manifest - just key and translated_content."""
#     key: str
#     translated_content: Optional[str] = None


# class ManifestScreenData(BaseModel):
#     data_id: str
#     data: Union[dict, list]
#     updated_by: Optional[str] = None


# class ClientManifest(BaseModel):
#     class LanguageInfo(BaseModel):
#         language_id: str
#         autonym_script: Optional[str] = None
#         learning_platform: Optional[bool] = None
#         country: Optional[str] = None
#         country_code: Optional[str] = None
#         latitude: Optional[float] = None
#         longitude: Optional[float] = None
#         version: Optional[float] = None

#     class CertificateProfileInfo(BaseModel):
#         certificate_profile_id: str
#         slug: str
#         country_code: str
#         country_name: Optional[str] = None
#         certificate_template: Optional[str] = None
#         current_version: Optional[str] = None

#     class CategoryManifest(BaseModel):
#         category_id: str
#         title: Optional[str] = None
#         translated_caption: Optional[str] = None
#         slug: Optional[str] = None
#         description: Optional[str] = None
#         assets: List[str] = []
#         modules: List[ManifestModule] = []
#         download_size: int = 0

#     language: LanguageInfo
#     certificate_profile: Optional[CertificateProfileInfo] = None
#     categories: List[CategoryManifest] = []
#     onboarding_questions: Optional[List[Any]] = []
#     transcriptions: List[ManifestTranscription] = []
#     screen_data: List[ManifestScreenData] = []
#     language_assets: List[str] = []
#     UserFeedback: List[Any] = []


from typing import Any, List, Optional, Union
from pydantic import BaseModel
from app.schemas.key_learning_points import KeyLearningPointResponse


class ManifestResourceRef(BaseModel):
    resource_id: str
    slug: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    version: Optional[float] = None
    order: Optional[int] = None
    content: Optional[str] = None
    icon: Optional[str] = None

class ManifestModule(BaseModel):
    module_id: str
    slug: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    version: Optional[float] = None
    status: Optional[str] = None
    icon: Optional[str] = None
    asset_total_size_mb: float = 0.0
    videos: List[ManifestResourceRef] = []
    action_cards: List[ManifestResourceRef] = []
    practical_procedures: List[ManifestResourceRef] = []
    drugs: List[ManifestResourceRef] = []
    keylearning_points: List[KeyLearningPointResponse] = []

class ManifestTranscription(BaseModel):
    """Flattened transcription for manifest - just key and translated_content."""
    key: str
    translated_content: Optional[str] = None

class ManifestScreenData(BaseModel):
    data_id: str
    data: Union[dict, list]
    updated_by: Optional[str] = None

class CertificateModuleRef(BaseModel):
    """Simplified module reference for certificate profile - just ID, title, and scores."""
    module_id: str
    slug: Optional[str] = None
    title: Optional[str] = None
    weightage: Optional[float] = 1.0
    passing_percentage: Optional[float] = 75.0
    mandatory: Optional[bool] = False
    order: Optional[int] = None

class ClientManifest(BaseModel):
    class LanguageInfo(BaseModel):
        language_id: str
        autonym_script: Optional[str] = None
        learning_platform: Optional[bool] = None
        country: Optional[str] = None
        country_code: Optional[str] = None
        latitude: Optional[float] = None
        longitude: Optional[float] = None
        version: Optional[float] = None

    class CertificateProfileInfo(BaseModel):
        certificate_profile_id: str
        slug: str
        country_code: str
        country_name: Optional[str] = None
        certificate_template: List[str] = []
        current_version: Optional[str] = None
        modules: List[CertificateModuleRef] = []

    class CategoryManifest(BaseModel):
        category_id: str
        title: Optional[str] = None
        translated_caption: Optional[str] = None
        slug: Optional[str] = None
        description: Optional[str] = None
        assets: List[str] = []
        modules: List[ManifestModule] = []
        download_size_mb: float = 0.0

    language: LanguageInfo
    certificate_profile: Optional[CertificateProfileInfo] = None
    categories: List[CategoryManifest] = []
    onboarding_questions: Optional[List[Any]] = []
    transcriptions: List[ManifestTranscription] = []
    screen_data: List[ManifestScreenData] = []
    language_assets: List[str] = []
    UserFeedback: List[Any] = []