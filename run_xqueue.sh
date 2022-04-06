docker build . -t xqueue_img
docker rm -f xqueue_cont 2> /dev/null || true
docker run -itd -p 8040:8040 --name xqueue_cont xqueue_img
echo "XQueue is running at http://localhost:8040"