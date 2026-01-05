CREATE TABLE Privateigentuemer (
ssn INT,
steuer_id INT CHECK (steuer_id > 0),
eigentuemer_id INT NOT NULL,

primary key (ssn)
);

INSERT INTO Privateigentuemer VALUES
                                  (1, 11111, 1),
                                  (2, 22222, 2),
                                  (3, 33333, 3),
                                  (4, 44444, 4),
                                  (5, 55555, 5),
                                  (6, 66666, 6),
                                  (7, 77777, 7);
