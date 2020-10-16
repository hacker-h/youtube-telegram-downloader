

class StorageInterface(ABC):
    """
    Abstract class to implement different backends
    """

    def __init__(self, path):
        """
        Path to root folder, that will contain downloaded files
        """
        self.path = path


    @abstractmethod
    def upload(self, file):
        """
        Upload a single file
        """
        raise NotImplementedError
    
    def upload_multiple(self, files):
        """
        Upload multiple files
        """
        raise NotImplementedError
