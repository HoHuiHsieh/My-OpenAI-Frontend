"""
User scopes definition
"""

# Define available scopes


class SCOPES:
    """Available user scopes"""
    ADMIN_SCOPE = "admin"
    MODELS_READ = "models:read"
    CHAT_BASE = "chat:base"
    EMBEDDINGS_BASE = "embeddings:base"
    AUDIO_TRANSCRIBE = "audio:transcribe"

    @classmethod
    def keys(cls):
        """Return all scope keys"""
        return [
            cls.ADMIN_SCOPE,
            cls.MODELS_READ,
            cls.CHAT_BASE,
            cls.EMBEDDINGS_BASE,
            cls.AUDIO_TRANSCRIBE
        ]
