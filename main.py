from random import randint
from dotenv import load_dotenv

load_dotenv()
from core import utils
from core.utils.sso_admin_utils import get_ps_list_for_account

print("Hello World!")

from core import utils
from core.handlers.aws_acc_handler import AWS
from core.authentication.aws_client_factory import AWSClientFactory


def main():

    # aws_handler = AWS(AWSClientFactory())
    for instance_arn in utils.INSTANCE_ARNS:
        print(get_ps_list_for_account(instance_arn, "123456789012"))


if __name__ == "__main__":
    main()
