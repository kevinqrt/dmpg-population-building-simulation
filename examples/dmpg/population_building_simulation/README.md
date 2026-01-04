# Architektur Population Building Simulation

## Grund Aufbau

**Menschen leben in Häusern → Arbeitszeit beginnt → Pull-System zieht Arbeiter aus Häusern → Menschen arbeiten → Menschen kehren zurück nach Hause**

Kernkomponenten:

- Human erbt von `Entity`
- House erbt von `Storage`
- Workplace erbt von `Server`
- Pull-System umgesetzt durch den `Storage-Manager`

## Bevölkerung/Humans (Entity)

Die Bevölkerung besteht aus einzelnen Menschen, die jeweils bestimmte Eigenschaften besitzen, z. B.:

- Demografische Daten (Alter, Beruf, Qualifikation)
- Arbeitszeiten bzw. Schichtpläne
- Zugehörigkeit zu einem Haushalt (Haus)

Jeder Bürger hat außerdem einen täglichen Ablauf, der typischerweise aus folgenden Phasen besteht:

1. Aufenthalt zu Hause (z. B. Schlafen, Freizeit)
2. Weg zur Arbeit
3. Arbeitszeit im entsprechenden Arbeitsplatz
4. Rückkehr nach Hause

## House (Storage)

Häuser fungieren als eine Art Speicherort für Menschen, aber auch als Organisationseinheit, die Menschen an Arbeitsplätze schickt:

Hauptfunktionen der Häuser:

- Beherbergen der Menschen (Speicherfunktion)
- Einreihen der arbeitsfähigen Menschen in Arbeitswarteschlangen

## Workplace (Server)

Ein Arbeitsplatz ist ein **aktiver Verbraucher** von Arbeitskraft.
Er besitzt:

- Arbeitszeiten
- Eine Kapazität, wie viele Menschen gleichzeitig dort arbeiten können
- Verarbeitungslogik: Sobald ein Arbeiter „gezogen“ wurde, beginnt Arbeitsprozess, die Dauer wird entsprechend den definierten Schichtplänen entnommen

### Ablauf Arbeitsplatz

1. Der Arbeitsplatz öffnet zu seiner festgelegten Zeit.
2. Er fragt beim Pull-System an: „Ich brauche X Arbeiter.“
3. Das Pull-System liefert passende Bürger aus den Häusern.
4. Die Bürger arbeiten dort, bis die Schicht vorbei ist.
5. Nach Schichtende werden sie **automatisch zurück nach Hause geschickt**.

Der Arbeitsplatz ist also ein **Server**, der Bürger „verarbeitet“, um Output zu erzeugen.

## Pull-System (StorageManager)

Dient als **zentrales Steuerungssystem** zwischen Häusern und Arbeitsplätzen.

Funktionen des Pull-Systems:

- Liefert Bürger an Arbeitsplätze nur dann, wenn diese aktiv danach fragen
- Arbeitet nachfragebasiert (Pull)
- Prüft, welche Bürger für den Arbeitsplatz geeignet sind (`AgeGroup`)
- Achtet auf Arbeitszeiten (`WorkScheduleWeek`), Verfügbarkeit und Qualifikation
