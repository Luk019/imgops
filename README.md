Just login using:

gcloud auth login

then run script:

./setup_infrastructure.sh YOUR_PROJECT_ID

Remember to have .ssh key on your machin script use it to copy to new created machine.

After all use this comand to send picture to the bucket:
gcloud storage cp books.png gs://bucket-cloud-zaliczenie/books.png --custom-metadata=rotation-angle=172,output-path=/home/user/incoming/

If custom metadata not set then default value:
rotation-angle=90
output-path=home directory of the user

PS. Script is set to use in home directrory of the user (else u need to edit it)
