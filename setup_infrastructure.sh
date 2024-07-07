#!/bin/bash

# Sprawdzenie, czy podano argument z ID projektu
if [ -z "$1" ]; then
  echo "Brak ID projektu. Użycie: ./setup_infrastructure.sh PROJECT_ID"
  exit 1
fi

PROJECT_ID=$1
SSH_KEY_PATH=~/.ssh/id_rsa

# Ustawienie projektu
gcloud config set project $PROJECT_ID

# Pobranie informacji o zalogowanym użytkowniku
USER_EMAIL=$(gcloud config get-value account)

# Wyciągnięcie nazwy użytkownika z JSON
USER_NAME=$(echo $USER_EMAIL | awk -F'@' '{print $1}')

# Włączanie niezbędnych API
gcloud services enable compute.googleapis.com
gcloud services enable pubsub.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable storage-api.googleapis.com

# Tworzenie maszyny wirtualnej
gcloud compute instances create my-vm \
    --zone=europe-north1-a \
    --machine-type=e2-micro \
    --image=debian-11-bullseye-v20240611 \
    --image-project=debian-cloud \
    --boot-disk-size=10GB \
    --tags=http-server,https-server \
    --metadata=startup-script='#!/bin/bash
      sudo apt-get update
      sudo apt-get install -y python3 python3-pip wget
      sudo pip3 install ansible'
	--metadata ssh-keys="$USER_NAME:$(cat $SSH_KEY_PATH.pub)"
	
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='get(projectNumber)')

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --role roles/storage.admin \
    --member serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com

# Pobranie zewnętrznego IP maszyny wirtualnej
VM_EXTERNAL_IP=$(gcloud compute instances describe my-vm --zone=europe-north1-a --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

# Tworzenie koszyka Cloud Storage
gcloud storage buckets create --location=europe-north1 gs://bucket-cloud-zaliczenie
gsutil iam ch user:ul0190828@gmail.com:objectCreator,objectViewer gs://bucket-cloud-zaliczenie

# Konfiguracja powiadomień dla koszyka
gcloud storage buckets notifications create gs://bucket-cloud-zaliczenie --topic=storage-notify-topic

# Konfiguracja powiadomień dla koszyka
gcloud storage notification create gs://bucket-cloud-zaliczenie --payload-format=JSON --topic=storage-notify-topic \
    --object-name-prefix="" --event-types=OBJECT_FINALIZE

# Budowa i wdrażanie aplikacji na Cloud Run
cd app
gcloud builds submit --region=us-west2 --tag gcr.io/$PROJECT_ID/image-transform .
gcloud run deploy image-transform --image gcr.io/$PROJECT_ID/my-app --platform managed --region=europe-north1 --allow-unauthenticated

SERVICE_URL=$(gcloud run services describe image-transform --platform managed --region europe-north1 \
  | grep -E '^URL:' \
  | awk '{print $2}')
  
  
# Utworzenie subskrypcji Pub/Sub
gcloud pubsub subscriptions create storage-subscription --topic=storage-notify-topic

cd ~/imgops

# Generowanie pliku hosts
cat <<EOL > hosts
[my-vm]
$VM_EXTERNAL_IP ansible_user=$USER_NAME ansible_ssh_private_key_file=$SSH_KEY_PATH

[cloud-run]
$SERVICE_URL
EOL

ansible-playbook -i hosts setup_vm.yml
