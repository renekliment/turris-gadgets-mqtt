# Turris Gadgets Playground (MQTT-centered)

## K čemu je to dobré

- Turris Dongle je prakticky sériová linka a k té se může bez problému připojit pouze jedna aplikace a pokud chceme, aby více aplikací přistupovalo ke Gadgetům, je třeba něco jako brána (což je právě `turrisGadgets_over_mqtt.py`)
- odstiňuje aplikace od nízkoúrovnějšího rozhraní poskytovaného Donglem a poskytuje zaběhlé (snadno se zapojí do stávající IoT infrastruktury) _vyšší-úrovňové_ rozhraní (je velmi, velmi jednoduché na použití ať už aplikacemi, či _ručně_)
- pomocí ACL na MQTT brokeru můžeme jednotlivým aplikacím nastavovat oprávnění k určitým zařízením, ať už co mohou ovládat, nebo jaké zprávy od jakých zařízeních mohou příjmat

## Více o MQTT
[Skvělý seriál o MQTT v angličtině](http://www.hivemq.com/mqtt-essentials-wrap-up/) je na blogu HiveMQ.
Adam Hořčica měl na LinuxDays 2014 [přednášku o protokolech pro IoT (YouTube)](https://www.youtube.com/watch?v=nsT1wlbAKug), jsou k ní i [slajdy](https://www.linuxdays.cz/2014/video/Adam_Horcica-Komunikacni_protokoly_pro_IoT.pdf).

## Instalace mosquitto (MQTT broker)
```
opkg install mosquitto mosquitto-client
/etc/init.d/mosquitto enable
/etc/init.d/mosquitto start
```
**VAROVÁNÍ:** Je velmi vhodné mosquitto zabezpečit, obzvlášť, pokud máte router dostupný z internetu!
**POZNÁMKA:** Je vhodné (ale ne nutné) si zkompilovat novější verzi _mosquitta_ s podporou WebSockets.

## Instalace python modulu pro práci se sériovým portem
```
opkg install pyserial
```

## Instalace python setup tools
```
wget https://bootstrap.pypa.io/ez_setup.py
python ez_setup.py --insecure
```

## Instalace MQTT python modulu
```
wget http://git.eclipse.org/c/paho/org.eclipse.paho.mqtt.python.git/snapshot/org.eclipse.paho.mqtt.python-1.1.tar.gz
tar xzf org.eclipse.paho.mqtt.python-1.1.tar.gz
cd org.eclipse.paho.mqtt.python-1.1
python setup.py install
```

## Instalace MPD python modulu - potřeba pouze pro demo s MPD
```
wget https://github.com/Mic92/python-mpd2/archive/v0.5.4.tar.gz
tar xzf v0.5.4.tar.gz
cd python-mpd2-0.5.4
python setup.py install
```

## Symlink pro python
`ln -s /usr/bin/python2.7 /usr/bin/python2`

## Nastavení MQTT brány
V souboru `turrisGadgets_over_mqtt.py` nastavíme v sekci CONFIG:
1. údaje pro připojení k MQTT brokeru (můžeme ponechat výchozí, pokud jsme nic neměnili)
2. sériová čísla Gadgetů - jsou to klíče v poli devices
3. podle potřeb si upravíme příslušné _mqttPath_

## Spuštění Gadgets <---> MQTT brány
**VAROVÁNÍ:** Skript vždy po spuštění vypne alarm/pípání a oba výstupy (zásuvky / relé), aby se dostal do definovaného stavu.
1. Stáhneme obsah repositáře a umístíme např. do /root/turris-gadgets-playground/
2. `python /root/turris-gadgets-playground/turrisGadgets_over_mqtt.py`

Pokud vše funguje a chceme nechat skript puštěný i po odhlášení z Turrisu:
1. `opkg install screen`
2. `screen -dmS turrisGadgets_over_mqtt /root/turris-gadgets-playground/turrisGadgets_over_mqtt.py`

## Testování komunikace s Gadgety
Poslouchání zpráv od Gadgetů: `mosquitto_sub -h 192.168.1.1 -t "turrisGadgets/#" -v`, kde případně upravíme IP adresu Turrisu, na kterém běží mosquitto a prefix, pod kterým se Gadgety nacházejí. Můžeme pustit jak na Turrisu, tak z kteréhokoliv zařízení, které tento nástroj obsahuje a může se na Turris po síti dostat.

Spínání zásuvek: 
```
mosquitto_pub -h 192.168.1.1 -t turrisGadgets/room/socket/lamp/control -m 1
mosquitto_pub -h 192.168.1.1 -t turrisGadgets/room/socket/lamp/control -m 0
```
Mezi přepínáním stavu _reléových_ zařízení je třeba pár sekund vyčkat.

## Nastavení demo aplikací
Provádí se v příslušných souborech. Jedná se o nastavení:
1. údajů pro připojení k MQTT brokeru (můžeme ponechat výchozí, pokud jsme nic neměnili)
2. prefixu, který používáme pro Gadgety (pokud jsme ho změnili v souboru nastavení brány)
3. jiných údajů (pro připojení k MPD, Twitteru, ...; pokud jsou relevantní) 
4. pokud jsme provedli změnu cesty komponent, musíme změnu reflektovat i v kódu - např. z _room/socket/lamp_ jsme udělali _room/socket/heater_