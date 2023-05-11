echo "=============VIDEO SERVER============"
echo "0. Installation"
echo "1. Build docker image"
echo "2. Start docker container"
echo "3. Logs container"
echo "4. Stop & remove container"

while :
do 
	read -p "Run with: " input
	case $input in
        0)
        pip3 install -e .
        export FLASK_ENV=development
        break
        ;;
		1)
        docker rmi -f lambiengcode/video-server
		docker build -t lambiengcode/video-server .
		break
		;;
		2)
		docker run --name video-server -p 5050:5050 -d lambiengcode/video-server:latest
		break
        ;;
		3)
		docker logs -f video-server
		break
        ;;
		4)
        docker stop video-server
		docker rm video-server
		break
        ;;
        *)
		;;
	esac
done