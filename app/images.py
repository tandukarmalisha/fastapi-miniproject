from imagekitio import ImageKit
import os
from dotenv import load_dotenv

load_dotenv()

# In Version 5.0.0, the initialization looks like this:
imagekit = ImageKit(
    private_key=os.getenv("IMAGEKIT_PRIVATE_KEY"),
    public_key=os.getenv("IMAGEKIT_PUBLIC_KEY"),
    url_endpoint=os.getenv("IMAGEKIT_URL_ENDPOINT")
)