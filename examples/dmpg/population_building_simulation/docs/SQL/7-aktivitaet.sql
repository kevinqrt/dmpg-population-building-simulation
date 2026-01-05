CREATE TABLE Aktivitaet (
ziel_id INT,
startzeit TIME,
endzeit TIME,

PRIMARY KEY (ziel_id, startzeit)
);

INSERT INTO Aktivitaet VALUES
                           (1, '09:00', '17:00'),
                           (2, '18:00', '22:00'),
                           (3, '07:00', '08:30'),
                           (4, '15:00', '17:00'),
                           (5, '16:00', '18:00'),
                           (6, '19:00', '21:00'),
                           (7, '20:00', '23:00');
