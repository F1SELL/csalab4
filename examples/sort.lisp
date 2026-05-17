(begin
  (setq a (- (in 0) 48))
  (in 0)
  (setq b (- (in 0) 48))
  (in 0)
  (setq c (- (in 0) 48))
  (in 0)

  (if (> a b)
      (begin
        (setq t a)
        (setq a b)
        (setq b t))
      0)
  (if (> b c)
      (begin
        (setq t b)
        (setq b c)
        (setq c t))
      0)
  (if (> a b)
      (begin
        (setq t a)
        (setq a b)
        (setq b t))
      0)

  (out 1 (+ 48 a))
  (out 1 32)
  (out 1 (+ 48 b))
  (out 1 32)
  (out 1 (+ 48 c))
  (out 1 10))
