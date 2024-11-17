rotate_logs() {
  local logfile=$1
  local logdir="tests/old"
  local counter=1

  mkdir -p $logdir

  while [ -f "$logdir/$(basename "$logfile").${counter}" ]; do
    ((counter++))
  done

  if [ -f "$logfile" ]; then
    mv "$logfile" "$logdir/$(basename "$logfile").${counter}"
  fi
}

rotate_logs "tests/serve.log"
rotate_logs "tests/web.log"
rotate_logs "tests/serve.err"
rotate_logs "tests/web.err"

export PYTHONUNBUFFERED=1
nohup .conda/bin/python serve/serve.py >tests/serve.log 2>tests/serve.err &
UVICORN_PID=$!
disown $UVICORN_PID

nohup stdbuf -oL -eL pnpm -C web run dev >tests/web.log 2>tests/web.err &
PNPM_PID=$!
disown $PNPM_PID

cleanup() {
  echo "Stopping services..."

  if kill -0 $UVICORN_PID 2>/dev/null; then
    kill $UVICORN_PID
  fi 

  if kill -0 $PNPM_PID 2>/dev/null; then
    kill $PNPM_PID
  fi 

  wait $UVICORN_PID
  wait $PNPM_PID

}

multitail -s 2 -C -T -cT ansi tests/serve.log tests/serve.err tests/web.log tests/web.err 
MULTITAIL_PID=$!

trap cleanup SIGINT SIGTERM
trap cleanup EXIT

wait $UVICORN_PID
wait $PNPM_PID
