#Alle Eigentümer auflisten
SELECT SSN, Vorname, Nachname, LEBENSALTER
FROM Person
WHERE istEigentuemer = TRUE;

#Wohnungen mit Barrierefreiheit
SELECT Wohnungsnummer, Ausstattung, Bewohner_Anzahl
FROM Wohnung
WHERE BARRIEREFREI = TRUE;

#Eigentümer mit ihren Wohnungen
SELECT p.SSN, p.Vorname, p.Nachname, w.Wohnungsnummer, w.Ausstattung
FROM Person p
         INNER JOIN Wohnung w ON p.SSN = w.Eigentuemer_SSN;

#Personen und ihre Aktivitäten
SELECT p.Vorname, p.Nachname, a.Name as Aktivitaet
FROM Person p
         INNER JOIN Gemachte_Aktivitaet ga ON p.SSN = ga.SSN
         INNER JOIN Aktivitaet a ON ga.Aktivitaet_ID = a.Aktivitaet_ID;

#Alle Wohnungen mit (oder ohne) Eigentümer
SELECT w.Wohnungsnummer, w.Ausstattung,
       p.Vorname, p.Nachname
FROM Wohnung w
         LEFT JOIN Person p ON w.Eigentuemer_SSN = p.SSN;

#Alle Personen mit ihren Zeitplänen
SELECT p.Vorname, p.Nachname,
       z.Startzeit, z.Dauer
FROM Person p
         LEFT JOIN Zeitplan z ON p.Zeitplan_ID = z.Zeitplan_ID;

#Alle Adressen aus Wohnungen UND Aktivitäten
-- Adressen von Gebäuden/Wohnungen
SELECT DISTINCT a.Ort, a.PLZ, 'Wohnadresse' as Quelle
FROM Adresse a
         INNER JOIN Gebaeude g ON a.Adresse_ID = g.Adresse_ID

UNION ALL

-- Adressen von Aktivitäten
SELECT DISTINCT a.Ort, a.PLZ, 'Aktivitätsadresse' as Quelle
FROM Adresse a
         INNER JOIN Aktivitaet akt ON a.Adresse_ID = akt.Adresse_ID;

#Lange und kurze Aktivitäten zusammenfassen
-- Kurze Aktivitäten (< 60 Minuten)
SELECT p.Vorname, a.Name as Aktivitaet, z.Dauer
FROM Person p
         JOIN Gemachte_Aktivitaet ga ON p.SSN = ga.SSN
         JOIN Aktivitaet a ON ga.Aktivitaet_ID = a.Aktivitaet_ID
         JOIN Zeitplan z ON p.Zeitplan_ID = z.Zeitplan_ID
WHERE z.Dauer < 60

UNION

-- Lange Aktivitäten (> 120 Minuten)
SELECT p.Vorname, a.Name as Aktivitaet, z.Dauer
FROM Person p
         JOIN Gemachte_Aktivitaet ga ON p.SSN = ga.SSN
         JOIN Aktivitaet a ON ga.Aktivitaet_ID = a.Aktivitaet_ID
         JOIN Zeitplan z ON p.Zeitplan_ID = z.Zeitplan_ID
WHERE z.Dauer > 120;

#Durchschnittliche Bewohnerzahl pro Stadt
SELECT a.Ort, AVG(w.Bewohner_Anzahl) as Durchschnitt_Bewohner
FROM Wohnung w
         JOIN Gebaeude g ON w.Gebaeude_ID = g.Gebaeude_ID
         JOIN Adresse a ON g.Adresse_ID = a.Adresse_ID
GROUP BY a.Ort;

#Personen mit hoher Priorität-Bedürfnisse
SELECT p.Vorname, b.Name as Beduerfnis, b.Prioritaet
FROM Person p
         JOIN Beduerfniszuordnung bz ON p.SSN = bz.SSN
         JOIN Beduerfnis b ON bz.Beduerfnis_ID = b.Beduerfnis_ID
WHERE b.Prioritaet > 500;










