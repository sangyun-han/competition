#!/usr/bin/env python3
import logging
import boto3
import os.path
import time
import constant
import util

from botocore.exceptions import ClientError
from constant import PERSISTENT_VALUE_FILE_PATH, REGION, \
                     BUCKET_NAME, DATA_DIRECTORY, SEGMENT_PATH, LAMBDA_PATH, \
                     S3_BUCKET_POLICY_NAME_FOR_PERSONALIZE, S3_POLICY_NAME_FOR_ROLE_FOR_PERSONALIZE, S3_ROLE_NAME_FOR_PERSONALIZE,S3_BUCKET_POLICY_NAME_FOR_PINPOINT, S3_POLICY_NAME_FOR_ROLE_FOR_PINPOINT, S3_ROLE_NAME_FOR_PINPOINT, LAMBDA_POLICY_NAME, LAMBDA_ROLE_NAME, ML_POLICY_NAME, ML_ROLE_NAME, \
                     TITLE, USER, TITLE_READ, TITLE_DATASET, USER_DATASET, TITLE_READ_DATASET, DSG, DSG_NAME, \
                     SOLUTION_NAME_SIMS, SOLUTION_NAME_UP, SOLUTION_SIMS, SOLUTION_UP, SOLUTION_VERSION_SIMS, SOLUTION_VERSION_UP, FILTER_UP, CAMPAIGN_NAME_SIMS, CAMPAIGN_NAME_UP, CAMPAIGN_SIMS, CAMPAIGN_UP, \
                     FUNCTION_NAME, \
                     ML_NAME, APPLICATION_NAME, SEGEMENT_NAME, CAMPAIGN_NAME, EMAIL_NAME, ADDRESS, HTML_TEXT
from persistent_value import PersistentValues, write 

# aws clients
personalize = boto3.client('personalize', region_name=REGION)
personalize_runtime = boto3.client('personalize-runtime', region_name=REGION)

s3 = boto3.client('s3', region_name=REGION)
iam_client = boto3.client('iam', region_name=REGION)
iam_resource = boto3.resource('iam', region_name=REGION)
pinpoint = boto3.client('pinpoint', region_name=REGION)
function = boto3.client('lambda')

def delete_personalize_campaign(campaignArn, campaignName):
    try:
      personalize.delete_campaign(campaignArn=campaignArn)
      util.wait_until_status(
          lambdaToGetStatus=lambda _="": personalize.describe_campaign(campaignArn=campaignArn)['campaign']['status'],
          messagePrefix=f"Deleting {campaignName} campaign...",
          expectedStatus="DELETED")

    except:
        logging.info(f"The {campaignName} campaign has been deleted.")

def delete_filter(filter_arn):
    logging.info("Delete filter: " + filter_arn)
    personalize.delete_filter(filterArn=filter_arn)

    time.sleep(60) # wait until filter has been deleted

def delete_dataset(arns):
    logging.info("Delete dataset: " + ", ".join(arns))
    for arn in arns:
        personalize.delete_dataset(datasetArn=arn)

    logging.info("Wait until datasets are deleted... It takes 2 minutes.")
    time.sleep(120)

def delete_dataset_group(dsg_arn):
    personalize.delete_dataset_group(datasetGroupArn=dsg_arn)

    try:
        util.wait_until_status(
            lambda _="": personalize.describe_dataset_group(datasetGroupArn=dsg_arn)[
                "datasetGroup"]["status"],
            "Deleting dataset group...",
            "Exception")

    except:
        logging.info("Dataset group has been deleted.")

def delete_schemas(arns):
    logging.info("Delete schema: " + ", ".join(arns))
    for arn in arns:
        personalize.delete_schema(schemaArn=arn)
  
def delete_role_and_policy(roleName, policyArn):
    logging.info("Delete role. Role name: " + roleName)
    iam_client.detach_role_policy(
        RoleName=roleName,
        PolicyArn=policyArn
    )

    time.sleep(5)

    iam_client.delete_role(RoleName=roleName)
    iam_client.delete_policy(PolicyArn=policyArn)

def make_bucket_empty():
    logging.info(f'Emptying S3 Bucket: {BUCKET_NAME}')

    bucket = boto3.resource('s3', region_name=REGION).Bucket(BUCKET_NAME)

    response = s3.list_objects_v2(Bucket=BUCKET_NAME)

    bucket.delete_objects(Delete={
      'Objects': list(map(lambda c: {'Key': c['Key']}, response["Contents"]))
    })


def delete_pinpoint_campaign():
    logging.info('Delete Campaign. Campaign name : {}'.format(CAMPAIGN_NAME))
    pinpoint.delete_campaign(ApplicationId=PersistentValues[APPLICATION_NAME],
                             CampaignId=PersistentValues[CAMPAIGN_NAME])

def delete_segment():
    logging.info('Delete Segment. Segment name : {}'.format(SEGEMENT_NAME))
    pinpoint.delete_segment(ApplicationId=PersistentValues[APPLICATION_NAME],
                            SegmentId=PersistentValues[SEGEMENT_NAME])

def delete_email_template():
    logging.info('Delete Email Template. Template name : {}'.format(EMAIL_NAME))
    pinpoint.delete_email_template(TemplateName=EMAIL_NAME)

def delete_recommender_configuration():
    logging.info('Delete ML Model. Model name : {}'.format(ML_NAME))
    pinpoint.delete_recommender_configuration(RecommenderId=PersistentValues[ML_NAME])

def delete_app():
    logging.info('Delete Pinpoint App. App name : {}'.format(APPLICATION_NAME))
    pinpoint.delete_app(ApplicationId=PersistentValues[APPLICATION_NAME])

def delete_function():
    logging.info('Delete Function. Function name : {}'.format(FUNCTION_NAME))
    function.delete_function(FunctionName=PersistentValues[FUNCTION_NAME])


if __name__ == "__main__":

    ########################################
    # pinpoint
    ########################################

    # pinpoint 관련 리소스 삭제
    delete_pinpoint_campaign()
    delete_segment()
    delete_email_template()
    delete_recommender_configuration()
    delete_app()

    # lambda 삭제
    delete_function()

    # pinpoint 관련 iam(role, policy) 삭제
    delete_role_and_policy(LAMBDA_ROLE_NAME, PersistentValues[LAMBDA_POLICY_NAME])
    delete_role_and_policy(ML_ROLE_NAME, PersistentValues[ML_POLICY_NAME])
    delete_role_and_policy(S3_ROLE_NAME_FOR_PINPOINT, PersistentValues[S3_POLICY_NAME_FOR_ROLE_FOR_PINPOINT])

    ########################################
    # personalize
    ########################################

    # personalize 관련 리소스 삭제
    delete_personalize_campaign(PersistentValues[CAMPAIGN_SIMS], "sims")
    delete_personalize_campaign(PersistentValues[CAMPAIGN_UP], "up")
    personalize.delete_solution(solutionArn=PersistentValues[SOLUTION_SIMS])
    personalize.delete_solution(solutionArn=PersistentValues[SOLUTION_UP])
    delete_filter(PersistentValues[FILTER_UP])
    delete_dataset([PersistentValues[TITLE_DATASET], PersistentValues[USER_DATASET], PersistentValues[TITLE_READ_DATASET]])
    delete_dataset_group(PersistentValues[DSG])
    delete_schemas([PersistentValues[TITLE], PersistentValues[USER], PersistentValues[TITLE_READ]])

    # s3 bucket 비우기. 버킷 삭제는 api를 제거면서.
    make_bucket_empty()

    # Personalize 관련 iam(role, policy) 삭제
    delete_role_and_policy(S3_ROLE_NAME_FOR_PERSONALIZE, PersistentValues[S3_POLICY_NAME_FOR_ROLE_FOR_PERSONALIZE])
