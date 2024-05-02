# gaep
Guideline adherent evidence-based physiotherapy

## Einleitung

Die "GAEP" Anwendung (Guideline Adherent Evidence Based Physiotherapy) ist eine innovative Softwarelösung, die speziell entwickelt wurde, um Physiotherapeut_Innen bei der effektiven Nutzung medizinischer Leitlinien zu unterstützen. Durch die Verwendung der fortschrittlichen GPT-Modelle von OpenAI ist GAEP in der Lage, Inhalte aus verschiedenen Leitlinien gezielt zu durchsuchen und nutzerspezifisch zusammenzufassen. Dies geschieht über ein interaktives Frage-Antwort-Dialogsystem, das direkt auf relevante Inhalte der Leitlinien Bezug nimmt und diese prägnant wiedergibt.

GAEP stellt eine wertvolle Ressource dar, die darauf abzielt, den Zugang zu und die Anwendung von evidenzbasierten Praktiken in der Physiotherapie zu vereinfachen und zu verbessern, wodurch letztendlich die Patientenversorgung optimiert wird.

Die Anwendung wurde u.a. mit der Mendix-Plattform entwickelt und steht als Open-Source-Prototyp zur Verfügung. Ziel dieser Dokumentation ist es, einen umfassenden Überblick über die Struktur und Funktionalität der Anwendung zu geben. Dies beinhaltet Details zur Architektur der Software, Anweisungen zur Installation und Einrichtung sowie Hinweise zur alltäglichen Nutzung.

## Zielgruppe

Die Anwendung "GAEP" richtet sich hauptsächlich an Physiotherapeut_Innen, die in ihrer täglichen Praxis auf evidenzbasierte Methoden zurückgreifen möchten. Obwohl medizinische Leitlinien in Deutschland primär für Ärzte konzipiert sind und eine wichtige Brücke zwischen Wissenschaft und klinischer Praxis schlagen, können auch Physiotherapeuten erheblich von deren Inhalten profitieren. Leitlinien bieten einen strukturierten Rahmen für physiotherapeutische Behandlungen und dienen als fundierte Argumentationsbasis in Gesprächen mit Patienten.

Allerdings sind diese Leitlinien oft in einer komplexen Fachsprache verfasst, die ohne spezifisches medizinisches Vorwissen schwer zu verstehen sein kann. Dies stellt insbesondere für Fachkräfte außerhalb der ärztlichen Berufsgruppe eine Herausforderung dar. Die GAEP-Anwendung adressiert dieses Problem, indem sie die Komplexität der Informationen reduziert und diese auf konkrete Fachfragen zugeschnitten aggregiert. Durch den Einsatz künstlicher Intelligenz wird nicht nur der Inhalt der Leitlinien präzise zusammengefasst, sondern auch die Sprache auf ein allgemein verständliches Niveau vereinfacht.

## Systemübersicht der GAEP-Anwendung

1. Benutzerinteraktion: Web-Browser: Der Benutzer interagiert mit der GAEP-Anwendung über einen Web-Browser. Dies ermöglicht eine benutzerfreundliche Oberfläche für den Zugriff auf die Anwendung.
2. Frontend: GAEP APP (Mendix Server FreeTier): Das Frontend der Anwendung läuft auf einem Mendix Server im FreeTier-Modus. Mendix ermöglicht eine schnelle Entwicklung und Bereitstellung von Web- und mobilen Anwendungen mit geringem Code-Aufwand. Hier verarbeitet die Anwendung Nutzereingaben und stellt die Benutzeroberfläche bereit.
3. Backend und Datenverarbeitung:
* FLASK Server (REST API): Der Flask Server dient als Backend der Anwendung und stellt eine REST API zur Verfügung. Über diese API werden Anfragen der GAEP App entgegengenommen und verarbeitet. Der Flask Server agiert als Mittler zwischen der Datenbank und der Anwendung, sowie zwischen der Anwendung und externen AI-Diensten.
* Guideline Database: Hier werden alle relevanten Daten und Informationen aus medizinischen Leitlinien gespeichert. Der Flask Server greift auf diese Datenbank zu, um spezifische Anfragen zu beantworten oder Daten für die Verarbeitung bereitzustellen.
5. Integration von künstlicher Intelligenz: GPT-4 (OpenAI API): Die Anwendung nutzt GPT-4, ein fortschrittliches, kostenpflichtiges Modell von OpenAI, um die Inhalte der medizinischen Leitlinien nutzerspezifisch zu analysieren und zusammenzufassen. Der Flask Server sendet Anfragen an die OpenAI API, erhält Antworten und leitet diese zurück an das Frontend, um sie dem Benutzer darzustellen.

![image](https://github.com/dozwa/gaep/blob/main/grafics/GAEP_architecture.png)

## Datenfluss
Der Datenfluss beginnt beim Benutzer, der über den Web-Browser Anfragen an die GAEP APP sendet.
Die GAEP APP leitet diese Anfragen an den Flask Server weiter, der wiederum notwendige Daten aus der Guideline Database abruft oder Anfragen an die OpenAI API sendet.
Antworten von der OpenAI API werden vom Flask Server empfangen und verarbeitet, bevor sie an das Frontend zurückgeschickt werden, um dem Benutzer die gewünschten Informationen anzuzeigen.

![image](https://github.com/dozwa/gaep/blob/main/grafics/GAEP_dataflow.png)

## Anforderungen für die GAEP-Anwendung
### Hardware-Anforderungen
**Benutzergeräte**
* Kompatibilität: Die Anwendung ist optimiert für die Nutzung auf Laptops und Tablets. Sie funktioniert ebenfalls auf aktuellen Smartphones, wobei die Benutzeroberfläche primär für größere Bildschirme (Tablets, Laptops) konzipiert ist.
* Mindestanforderungen: Spezifische Mindestanforderungen an die Hardware wurden nicht ermittelt, jedoch wurde die Anwendung erfolgreich auf ca. 4 Jahre alten Android Tablets und aktuellen Smartphones und Laptops getestet, ohne dass Performanceprobleme auftraten.
Server-Hardware:

**Virtualisierte Umgebung** 
Der Betrieb von Flask Server und SQL-Datenbank wurde auf virtuellen Servern mit folgenden Mindestspezifikationen erfolgreich getestet:
* Prozessor: zwei Kerne
* Arbeitsspeicher: 16 GB RAM

### Software-Anforderungen

**Betriebssysteme**
* Client-Geräte: Die Endbenutzer-Webanwendung ist kompatibel mit den Betriebssystemen, die die unten aufgeführten Browser unterstützen.
* Entwicklungsumgebung (Mendix): Für spezifische Anforderungen zur Mendix Software, insbesondere welche Betriebssysteme für die Bearbeitung des Frontends unterstützt werden, siehe Mendix-Homepage.

**Webbrowser**
Die Webanwendung wurde getestet und ist kompatibel mit:
* Google Chrome (Version 124.0.6367.62) unter macOS
* Safari (Version 17.4.1) unter macOS
* Google Chrome (Version 124) auf iPhone

**Server-Software**
Die notwendige Software zur Ausführung des Flask-Servers und der SQL-Datenbank wird in einer requirements.txt-Datei spezifiziert, welche alle benötigten Python-Bibliotheken und weitere Abhängigkeiten auflistet. Die Anwendung wurde mit Python 3.9.2 entwickelt.

### Netzwerkanforderungen

**Internetgeschwindigkeit**
* Empfohlen wird eine Internetverbindung, die den Transfer von JSON-Dateien mit bis zu 2 MB in wenigen Sekunden ermöglicht.

**Netzwerkkonfiguration**
Firewall-Einstellungen: Folgende Freigaben sind notwendig:
* Zugriff auf OpenAI-Server
* Zugriff auf Mendix-Server
* Portfreigabe für den Flask Server auf Port 5001

## Kontenanforderungen
**Mendix-Account**

Zweck: Ein Mendix-Account ist erforderlich für die Bearbeitung der Mendix-App und für das Deployment auf dem Mendix FreeTier.
Berechtigungen: Für die Nutzung der Mendix-Plattform sind keine speziellen Berechtigungen oder Rollen innerhalb des Accounts erforderlich.

## Datenschutzanforderungen

Verarbeitung medizinischer Daten: Die GAEP-Anwendung darf keine personenbezogenen Daten verarbeiten. Dies schließt speziell Patientendaten und andere sensible Informationen aus, um den Datenschutz zu gewährleisten.

## Compliance-Anforderungen:

DSGVO (Datenschutz-Grundverordnung): Die Anwendung muss die Anforderungen der Europäischen Datenschutz-Grundverordnung erfüllen. Dies beinhaltet die Einhaltung von Datenschutzprinzipien wie Datenminimierung, Zweckbindung und Transparenz.

## Installationsprozess und Einrichtung der GAEP-Anwendung
Der Installationsprozess der GAEP-Anwendung umfasst die Einrichtung der SQL-Datenbank, des Flask Servers und der Mendix-App. Hier sind die detaillierten Schritte zur korrekten Installation und Konfiguration:

### SQL-Datenbank
**Einrichten der Datenbank**
* Richten Sie eine eigene SQL-Datenbank auf einem geeigneten Server ein.
* Stellen Sie sicher, dass die Datenbankserver-Konfiguration den Anforderungen Ihrer Infrastruktur entspricht.
**Datenbank initialisieren**
* Laden Sie das leitlinien.sql File aus dem Repository herunter.
* Führen Sie das SQL-Script aus, um die Datenbank mit den notwendigen Strukturen und Daten zu befüllen.

### Flask Server
**Voraussetzungen installieren**
* Installieren Sie Python 3.9.2 und die erforderlichen Pakete, wie in der requirements.txt-Datei des Repositories aufgeführt.
* Laden Sie die Datei Empfehlung_Kreuzschmerz_COPD.xlsx herunter unter auf dem Server hoch.
* Laden Sie die Datei GAEP_Server.py herunter und auf dem Server in das selbe Verzeichnis hoch (alternativ den Pfad zu dem xlsx File manuell anpassen).
* Laden Sie die Datei prompt_helper.py herunter und auf dem Server in das selbe Verzeichnis hoch (alternativ den Pfad zu dem xlsx File manuell anpassen).
**Konfiguration**
* Konfigurieren Sie die Zugangsdaten für die SQL-Datenbank in der Datei gaep_server.py.
* Hinterlegen Sie die Zugangsdaten für die OpenAI API ebenfalls in gaep_server.py.
* Legen Sie die Nutzerdaten für den Zugriff auf den Flask Server in gaep_server.py fest.
* ggf. den Pfad zu dem xlsx File manuell anpassen in gaep_server.py.
**OpenAI Modelle konfigurieren**
Wählen Sie gegebenenfalls die spezifischen Modelle von OpenAI aus (z.B. Embedding Model, Completion Model) und aktualisieren Sie diese bei Bedarf in gaep_server.py.

### Mendix-App
**Konfiguration der Verbindungsdaten**
* Stellen Sie sicher, dass die Adresse und die Zugangsdaten des Flask Servers in der Mendix-App korrekt eingerichtet sind.
**Deployment**
* Deployen Sie die Mendix-App auf einem Mendix Server. Folgen Sie dabei den Anleitungen der Mendix-Plattform, um die App erfolgreich hochzuladen und zu konfigurieren.

## Sicherheit und Datenschutz

### Sicherheitsmaßnahmen
**Passwortverschlüsselung** 
Die Kommunikation mit dem Flask Server erfolgt unter Verwendung von Passwortverschlüsselung. Dies hilft, die Sicherheit der übertragenen Daten zu gewährleisten.
Prototyp-Status: Der aktuelle Entwicklungsstand der GAEP-Anwendung ist als Prototyp definiert. Es sollten zusätzliche Sicherheitsmaßnahmen in Betracht gezogen werden, bevor eine produktive Nutzung erfolgt.
**Eignung des Flask Servers** 
Der verwendete Flask Server ist in seiner Standardkonfiguration nicht für den Einsatz in einer Produktionsumgebung gedacht. Für einen Produktiveinsatz sollten robustere und sicherheitsorientierte Serverlösungen oder zusätzliche Sicherheitsschichten in Betracht gezogen werden.

### Datenschutz
Der Schutz und die Verwendung von Benutzerdaten in der GAEP-Anwendung werden durch folgende Maßnahmen geregelt:

**Datentrennung** 
Die Architektur des Servers, der die Mendix-App mit der OpenAI-API verbindet, ist so gestaltet, dass keine Nutzerdaten an OpenAI weitergeleitet werden. Dies verhindert, dass sensible oder personenbezogene Daten unbeabsichtigt an externe Dienste übertragen werden.
**Disclaimer**
Die Anwenderinnen werden beim Aufruf der Anwendung darauf hingewiesen, dass die Verarbeitung von personenbezogenen Daten mit der Anwendung nicht gestattet ist.
**Eingeschränkte Datenschutzmaßnahmen** 
Abgesehen von der oben genannten Datentrennung und dem Disclaimer wurden keine weiteren spezifischen Datenschutzmaßnahmen implementiert. Angesichts der Sensibilität medizinischer Daten ist es empfehlenswert, zusätzliche Datenschutzstrategien zu entwickeln und umzusetzen, insbesondere im Hinblick auf die Einhaltung der Datenschutz-Grundverordnung (DSGVO) und anderer relevanter Datenschutzbestimmungen.

### Empfehlungen für zukünftige Entwicklungen
Um die Sicherheit und den Datenschutz der GAEP-Anwendung zu verbessern, sollten folgende Maßnahmen in Betracht gezogen werden:

**Implementierung zusätzlicher Sicherheitsmaßnahmen** 
Dazu könnten gehören: Einsatz von HTTPS zur Verschlüsselung aller Datenübertragungen, robustere Authentifizierungs- und Autorisierungsmechanismen, und regelmäßige Sicherheitsüberprüfungen.
**Anpassung an Produktionsstandards** 
Überarbeitung der Serverkonfiguration und möglicherweise der Migration auf eine Plattform, die für den produktiven Einsatz besser geeignet ist.
**Datenschutzkonformität** 
Weiterentwicklung der Datenschutzpraktiken, um sicherzustellen, dass alle personenbezogenen Daten konform mit lokalen und internationalen Datenschutzgesetzen behandelt werden.

## Datenbankstruktur
Die GAEP-Anwendung verwendet eine strukturierte SQL-Datenbank, um medizinische Leitlinien und zugehörige Empfehlungen zu speichern und zu verwalten. Das Datenbankschema, wie im bereitgestellten Diagramm dargestellt, enthält mehrere Tabellen und Beziehungen, die eine detaillierte und geordnete Speicherung der Daten ermöglichen. Hier ist eine Beschreibung der wichtigsten Komponenten dieses Schemas:

**Tabelle Empfehlung**
* ID: Eindeutige Identifikationsnummer.
* Text: Der Volltext der Empfehlung.
* Grad: Gibt den Grad der Empfehlung an.
* Basis: Basis oder Grundlage der Leitlinie.
* Seite: Die spezifische Seite im Dokument, auf die sich eine Information bezieht.
* Nummer: Die Nummer der Empfehlung innerhalb der Leitlinie.
* Oberthema: Das Hauptthema der Empfehlung bspw. Medikamentöse Intervention
* Zwischenthema: zweite Themenebene
* Unterthema: dritte Themenebene
* OT_Text, ZT_Text, UT_Text: Textabschnitte für Oberthema, Zwischenthema und Unterthema.
* OT_Nummer, ZT_Nummer, UT_Nummer: Numerische Identifikatoren für die Themen.

Die Empfehlungstabelle verbindet spezifische Empfehlungen mit den jeweiligen Themen und bietet sowohl numerische als auch textbasierte Beschreibungen.

**Tabelle Empfehlungsdetail**
* ID: Eindeutige Identifikationsnummer.
* Leitlinie: Referenz auf die Leitlinie, zu der das Detail gehört.
* Position: Die spezifische Position des Details innerhalb der Leitlinie.
* Text: Detaillierte Beschreibung des Empfehlungsdetails.
* Bild: Bildmaterial oder grafische Darstellungen, die zur Empfehlung gehören.

Die Tabelle Empfehlungsdetail speichert detaillierte Informationen zu spezifischen Aspekten einer Empfehlung und enthält auch visuelle Materialien zur Unterstützung der textbasierten Inhalte.

**Tabelle Quelle**
* ID: Eindeutige Identifikationsnummer.
* Leitlinie: Referenz auf die Leitlinie.
* Nummer: Die Nummer oder der Identifier der Quelle innerhalb der Leitlinie.
* Details: Textuelle oder sonstige Details zur Quelle.
* Link: Ein Web-Link zur Quelle.

Die Quellentabelle stellt Informationen zur Verfügung, die den Ursprung und die Grundlage der in den Leitlinien enthaltenen Informationen verifizieren.

**Verbindungen zwischen den Tabellen**

Die Beziehungen zwischen den Tabellen sind durch Fremdschlüssel definiert, die eine integrierte und konsistente Navigation durch die Daten erlauben. Diese Struktur unterstützt effizient das Abrufen von Daten basierend auf thematischen oder inhaltlichen Verknüpfungen und gewährleistet die Datenintegrität über das gesamte Schema hinweg.

![image](https://github.com/dozwa/gaep/blob/main/grafics/GAEP_db.png)

## Quellcodedokumentation

Der Quellcode der ist ausführlich in der Python Datei gaep_server.py kommentiert. Auf eine deteillierte Beschreibung wird hier daher verzichtet.

## Support

Fragen zur Anwendung sollten innerhalb dieses Repositories geklärt werden.
