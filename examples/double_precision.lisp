(defun is_digit (ch)
  (if (< ch 48)
      0
      (if (> ch 57) 0 1)))

(defun read_number ()
  (begin
    (setq acc 0)
    (setq started 0)
    (setq cont 1)
    (loop cont
      (begin
        (setq ch (in 0))
        (if (= (is_digit ch) 1)
            (begin
              (setq started 1)
              (setq acc (+ (* acc 10) (- ch 48))))
            (if (= started 1)
                (setq cont 0)
                0))))
    acc))

(defun print_digit (d)
  (out 1 (+ 48 d)))

(begin
  (setq hi1 (- (in 0) 48))
  (in 0)
  (setq lo1 (- (in 0) 48))
  (in 0)
  (setq hi2 (- (in 0) 48))
  (in 0)
  (setq lo2 (- (in 0) 48))
  (in 0)

  (setq lo_sum (+ lo1 lo2))
  (setq carry 0)
  (if (>= lo_sum 10)
      (begin
        (setq lo_sum (- lo_sum 10))
        (setq carry 1))
      0)
  (setq hi_sum (+ hi1 hi2 carry))

  (out 1 (+ 48 hi_sum))
  (out 1 58)
  (out 1 (+ 48 lo_sum))
  (out 1 10))
