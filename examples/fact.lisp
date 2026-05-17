(func fact (n) {(check (= n 0) 1 (* n (fact (- n 1))))})
(out 1 (fact 5))
