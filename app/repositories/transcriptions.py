from app.models.transcriptions import Transcription, TranscriptionVersion
from app.models.languages import Language
from app.schemas.transcriptions import TranscriptionVersionCreate, TranscriptionVersionResponse, TranscriptionUpdate
from neomodel import db


class TranscriptRepository:
    @staticmethod
    def create_transcription(language_id: str, data: TranscriptionVersionCreate) -> TranscriptionVersionResponse:
        """Create a new transcription version.
        
        This creates a new version every time it's called. The version is created as 'draft'
        and needs to be manually set as current using set_current_version().
        """
        # Get Language directly
        language = Language.nodes.get_or_none(language_id=language_id)
        if not language:
            raise ValueError(f"Language {language_id} not found")

        # Define the monolithic key for this language's transcriptions
        # This ensures one container per language
        key = f"transcription_{language.language_id}"
        
        # Find or create Transcription container
        transcription = Transcription.nodes.get_or_none(key=key)
        if not transcription:
            transcription = Transcription(key=key).save()
        
        # Get the latest version number
        existing_versions = list(transcription.versions.all())
        if existing_versions:
            latest_version = max(v.version for v in existing_versions)
            new_version_number = latest_version + 0.1
        else:
            new_version_number = 1.0
        
        # Create new TranscriptionVersion (as draft)
        version = TranscriptionVersion(
            data=data.data,
            version=new_version_number,
            status="draft",
            created_by=data.updated_by or "System",
            updated_by=data.updated_by
        ).save()
        
        # Link version to container
        transcription.versions.connect(version)
        
        # Link container to Language
        language.transcriptions.connect(transcription)
        
        return TranscriptionVersionResponse(
            transcription_version_id=version.transcription_version_id,
            transcription_id=transcription.transcription_id,
            key=transcription.key,
            data=version.data,
            version=version.version,
            status=version.status,
            created_at=version.created_at,
            updated_at=version.updated_at,
            updated_by=version.updated_by
        )
    
    @staticmethod
    def set_current_version(transcription_id: str, version_id: str) -> TranscriptionVersionResponse:
        """Set a specific version as the current version for a transcription."""
        transcription = Transcription.nodes.get_or_none(transcription_id=transcription_id)
        if not transcription:
            raise ValueError(f"Transcription {transcription_id} not found")
        
        version = TranscriptionVersion.nodes.get_or_none(transcription_version_id=version_id)
        if not version:
            raise ValueError(f"TranscriptionVersion {version_id} not found")
        
        # Disconnect old current version
        transcription.current_version.disconnect_all()
        
        # Set new current version
        transcription.current_version.connect(version)
        
        # Update version status to active
        version.status = "active"
        version.save()
        
        return TranscriptionVersionResponse(
            transcription_version_id=version.transcription_version_id,
            transcription_id=transcription.transcription_id,
            key=transcription.key,
            data=version.data,
            version=version.version,
            status=version.status,
            created_at=version.created_at,
            updated_at=version.updated_at,
            updated_by=version.updated_by
        )
    
    @staticmethod
    def get_transcription(transcription_id: str):
        """Get a transcription with all its versions."""
        transcription = Transcription.nodes.get_or_none(transcription_id=transcription_id)
        if not transcription:
            raise ValueError(f"Transcription {transcription_id} not found")
        
        current_version = transcription.current_version.single()
        all_versions = list(transcription.versions.all())
        
        return {
            "transcription_id": transcription.transcription_id,
            "key": transcription.key,
            "current_version": {
                "transcription_version_id": current_version.transcription_version_id,
                "data": current_version.data,
                "version": current_version.version,
                "status": current_version.status,
                "created_at": current_version.created_at,
                "updated_at": current_version.updated_at,
                "updated_by": current_version.updated_by
            } if current_version else None,
            "versions": [
                {
                    "transcription_version_id": v.transcription_version_id,
                    "data": v.data,
                    "version": v.version,
                    "status": v.status,
                    "created_at": v.created_at,
                    "updated_at": v.updated_at,
                    "updated_by": v.updated_by
                } for v in all_versions
            ]
        }

    @staticmethod
    def get_all_transcriptions():
        """Get all transcriptions with their versions."""
        all_transcriptions = Transcription.nodes.all()
        
        result = []
        for transcription in all_transcriptions:
            current_version = transcription.current_version.single()
            all_versions = list(transcription.versions.all())

            result.append({
                "transcription_id": transcription.transcription_id,
                "key": transcription.key,
                "current_version": {
                    "transcription_version_id": current_version.transcription_version_id,
                    "data": current_version.data,
                    "version": current_version.version,
                    "status": current_version.status,
                    "created_at": current_version.created_at,
                    "updated_at": current_version.updated_at,
                    "updated_by": current_version.updated_by
                } if current_version else None,
                "versions": [
                    {
                        "transcription_version_id": v.transcription_version_id,
                        "data": v.data,
                        "version": v.version,
                        "status": v.status,
                        "created_at": v.created_at,
                        "updated_at": v.updated_at,
                        "updated_by": v.updated_by
                    } for v in all_versions
                ]
            })
        return result


    @staticmethod
    def update_transcription_data(version_id: str, data: TranscriptionUpdate) -> TranscriptionVersionResponse:
        """Update the data content of a transcription version."""
        version = TranscriptionVersion.nodes.get_or_none(transcription_version_id=version_id)
        if not version:
            raise ValueError(f"TranscriptionVersion {version_id} not found")
        
        if data.data is not None:
            version.data = data.data
            
        if data.updated_by:
            version.updated_by = data.updated_by
            
        version.save()
        
        transcription = version.transcription.single()
        key = transcription.key if transcription else "unknown"
        transcription_id = transcription.transcription_id if transcription else "unknown"
        
        return TranscriptionVersionResponse(
            transcription_version_id=version.transcription_version_id,
            transcription_id=transcription_id,
            key=key,
            data=version.data,
            version=version.version,
            status=version.status,
            created_at=version.created_at,
            updated_at=version.updated_at,
            updated_by=version.updated_by
        )
