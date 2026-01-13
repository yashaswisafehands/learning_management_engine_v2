from app.repositories.transcriptions import TranscriptRepository
from app.schemas.transcriptions import TranscriptionVersionCreate, TranscriptionUpdate


class TranscriptionService:
    @staticmethod
    def create_transcription(language_id: str, data: TranscriptionVersionCreate):
        return TranscriptRepository.create_transcription(language_id, data)
    
    @staticmethod
    def set_current_version(transcription_id: str, version_id: str):
        return TranscriptRepository.set_current_version(transcription_id, version_id)

    @staticmethod
    def get_transcription(transcription_id: str):
        return TranscriptRepository.get_transcription(transcription_id)

    @staticmethod
    def get_all_transcriptions():
        return TranscriptRepository.get_all_transcriptions()

    @staticmethod
    def update_transcription_data(version_id: str, data: TranscriptionUpdate):
        return TranscriptRepository.update_transcription_data(version_id, data)

    @staticmethod
    def get_transcriptions(include_versions: bool = False):
        return TranscriptRepository.get_all_transcriptions()


async def get_all_transcriptions(include_versions: bool = True):
    return TranscriptionService.get_all_transcriptions()
