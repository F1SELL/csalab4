(defun echo_name (ch)
  (if (= ch 10)
      0
      (begin
        (out 1 ch)
        (echo_name (in 0)))))

(begin
  (print "What is your name?\n")
  (print "Hello, ")
  (echo_name (in 0))
  (print "!\n"))
