import pytest
from faker import Faker

fake = Faker("dk_DK")


@pytest.fixture
def random_email_bytes():
    with open("src/resources/demo_pdf_img.eml") as mime_file:
        body = "".join(mime_file.readlines())
        mail_bytes = body.encode("utf-8")
    return mail_bytes


@pytest.fixture
def random_email():
    with open("src/resources/demo_pdf_img.eml") as fp:
        mail_str = str(fp.read())
    return mail_str


@pytest.fixture
def random_email_path():
    return "src/resources/demo_pdf_img.eml"
