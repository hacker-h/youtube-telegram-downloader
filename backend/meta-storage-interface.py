

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
    def upload(self, filepath): 
        """
        Upload a single file
        """
        raise NotImplementedError
    
    def upload_multiple(self, dirpath):
        """
        Upload multiple files 
        """
        raise NotImplementedError