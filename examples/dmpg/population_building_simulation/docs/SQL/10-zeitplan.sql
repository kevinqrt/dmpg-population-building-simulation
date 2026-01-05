CREATE TABLE Zeitplan (
zeitplan_id INT CHECK (zeitplan_id > 0),
startzeit TIME,
endzeit TIME,
dauer TIME,
wochentag enum ('Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'),

PRIMARY KEY (zeitplan_id),
CHECK (startzeit < endzeit)
);

INSERT INTO Zeitplan VALUES
                         (1, '08:00', '16:00', '08:00', 'Mo'),
                         (2, '09:00', '17:00', '08:00', 'Di'),
                         (3, '10:00', '18:00', '08:00', 'Mi'),
                         (4, '07:00', '15:00', '08:00', 'Do'),
                         (5, '06:00', '14:00', '08:00', 'Fr'),
                         (6, '12:00', '20:00', '08:00', 'Sa'),
                         (7, '13:00', '21:00', '08:00', 'So');

