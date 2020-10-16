

class MetaStorageInterface(ABC):
    """
    Abstract Class for implementing an backend
    """

    def __init__(self, path):
        """
        Output Path, -> google drive location
        """
        self.path = path
    
    
    @abstractmethod
    def upload(self, file):
        """
        Upload Single file
        """
        raise NotImplementedError
    
    def upload_multiple(self, files):
        """
        Upload more than one file
        """
        raise NotImplementedError