for dest in $(<allnetworks.txt); do
  scp ringo.py ${dest}:
done
