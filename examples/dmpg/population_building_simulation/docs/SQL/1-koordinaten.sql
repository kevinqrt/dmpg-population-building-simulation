CREATE TABLE Koordinaten (
koordinaten_id INT CHECK (koordinaten_id > 0),
breitengrad DECIMAL(10,8) NOT NULL,
laengengrad DECIMAL(11,8) NOT NULL,

PRIMARY KEY (koordinaten_id)
);

INSERT INTO Koordinaten VALUES
                            (1, 52.520008, 13.404954),
                            (2, 48.137154, 11.576124),
                            (3, 50.110924, 8.682127),
                            (4, 53.551086, 9.993682),
                            (5, 51.227741, 6.773456),
                            (6, 49.006889, 8.403653),
                            (7, 52.375892, 9.732010);







