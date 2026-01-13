from app.repositories.settings_screen import ScreenDataRepository
from app.schemas.settings_screen import ScreenDataVersionCreate, ScreenDataUpdate


class ScreenDataService:
    @staticmethod
    def create_screen_data(language_id: str, data: ScreenDataVersionCreate):
        return ScreenDataRepository.create_screen_data(language_id, data)
    
    @staticmethod
    def set_current_version(data_id: str, version_id: str):
        return ScreenDataRepository.set_current_version(data_id, version_id)

    @staticmethod
    def get_screen_data(data_id: str):
        return ScreenDataRepository.get_screen_data(data_id)

    @staticmethod
    def update_screen_data_data(version_id: str, data: ScreenDataUpdate):
        return ScreenDataRepository.update_screen_data_data(version_id, data)

    @staticmethod
    def get_settings_screens(include_versions: bool = False):
        # We always return versions structure from repo now
        return ScreenDataRepository.get_all_screen_data()


async def get_settings_screens(include_versions: bool = False):
    return ScreenDataService.get_settings_screens(include_versions)
