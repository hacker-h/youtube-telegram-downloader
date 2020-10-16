

class MetaStorageInterface(ABC):
    """
    Abstract class to implement diffrent backends
    """

    def __init__(self, path):
        """
        Output path/root folder
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