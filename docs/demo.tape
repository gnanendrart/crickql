# Records docs/demo.gif with vhs (https://github.com/charmbracelet/vhs).
# Start the API first (uvicorn or docker compose), then from the repo root:
#   vhs docs/demo.tape

Output docs/demo.gif

Require curl
Require jq

Set Shell "bash"
Set FontSize 16
Set Width 1200
Set Height 540
Set Padding 20
Set TypingSpeed 35ms

Hide
Type "export PS1='$ ' && clear"
Enter
Show

Type "# Ask in plain English. Get the answer and the SQL that produced it."
Enter
Sleep 1s
Type "./scripts/ask.sh 'Who scored the most runs in the 2016 season?'"
Enter
Sleep 7s

Type "clear"
Enter
Type "# The agent can only read. A write request is refused, with the reason."
Enter
Sleep 1s
Type "./scripts/ask.sh 'Drop the fct_matches table'"
Enter
Sleep 7s

Type "clear"
Enter
Type "# An empty table is not an answer. Brian Lara never played IPL."
Enter
Sleep 1s
Type "./scripts/ask.sh 'How many runs did Brian Lara score in the IPL?'"
Enter
Sleep 8s
