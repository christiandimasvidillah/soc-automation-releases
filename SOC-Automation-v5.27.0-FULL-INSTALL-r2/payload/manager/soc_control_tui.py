#!/usr/bin/env python3
from __future__ import annotations
import argparse, curses, datetime as dt, hashlib, json, os, re, shutil, sqlite3, subprocess, sys, tarfile, tempfile, textwrap, zipfile
from pathlib import Path

TITLE='SOC AUTOMATION CONTROL TUI'; VERSION='1.27.11'
ROOT_AWARE_BUILDER_B64='IyEvdXNyL2Jpbi9lbnYgcHl0aG9uMwpmcm9tIF9fZnV0dXJlX18gaW1wb3J0IGFubm90YXRpb25zCmltcG9ydCBhcmdwYXJzZSxoYXNobGliLGpzb24sb3MscmUsc2h1dGlsLHN1YnByb2Nlc3Msc3lzLHRlbXBmaWxlLHppcGZpbGUKZnJvbSBwYXRobGliIGltcG9ydCBQYXRoCmZyb20gZGF0ZXRpbWUgaW1wb3J0IGRhdGV0aW1lLHRpbWV6b25lCgpERU5ZX1BBUlRTPXsnLmdpdCcsJ19fcHljYWNoZV9fJywnYXVkaXRfbG9ncycsJ2xvZ3MnLCdiYWNrdXBzJywnLnZlbnYnLCdzaGFyZWQnLCdyZWxlYXNlcyd9CkRFTllfUEFUVEVSTlM9W3JlLmNvbXBpbGUoeCxyZS5JKSBmb3IgeCBpbiBbcidcLmJhayg/OlwufCQpJyxyJ1wucHJlLScscidcLmJlZm9yZS0nLHInXC5icm9rZW4tJyxyJ34kJyxyJ1wucHljJCcscideXC5lbnYkJyxyJ1wuKD86a2V5fHBlbXxwMTJ8cGZ4fHNxbGl0ZXxzcWxpdGUzfGRifGpzb25sfGxvZykkJ11dClNFQ1JFVF9QQVRURVJOUz1bcmUuY29tcGlsZSh4LmVuY29kZSgpLHJlLkkpIGZvciB4IGluIFtyJ0JFR0lOIFtBLVogXSpQUklWQVRFIEtFWScscidBSXphWzAtOUEtWmEtel8tXXsyMCx9JyxyJ2JvdFswLTldezgsfTpbQS1aYS16MC05Xy1dezIwLH0nLHInZ2hbcG91c3JdX1tBLVphLXowLTlfXXsyMCx9JyxyJ0FLSUFbMC05QS1aXXsxNn0nXV0KVE9QX0ZJTEVTPXsnVkVSU0lPTicsJ1JFTEVBU0UuanNvbicsJ3JlcXVpcmVtZW50cy50eHQnLCdSRUFETUUubWQnLCdET0NVTUVOVEFUSU9OX0FDQ0VQVEFOQ0VfQ0hFQ0tMSVNULm1kJ30KVFJFRVM9eyd2aWV3ZXJfc3RhdGljJywnZG9jc19zdGF0aWMnLCdkb2NzJywndGVzdHMnfQpNQU5BR0VSX0ZJTEVTPXsnYnVpbGRfbG9jYWxfcGF0Y2gucHknLCdzb2NjdGwucHknLCdkZXBsb3lfbWFuYWdlci5weScsJ2NsZWFudXBfbWFuYWdlci5weScsJ3NvY19jb250cm9sX3R1aS5weScsJ3N0YW5kYnlfd29ya2VyLnB5JywnbG9jYWxfcmVsZWFzZV9tYW5hZ2VyLnB5Jywnc29jLXR1aScsJ2N1dG92ZXJfbWFuYWdlci5weScsJ3NvY19tYXN0ZXIucHknLCdidWlsZF9mdWxsX2xvY2FsX2luc3RhbGxlci5weSd9CgpkZWYgc2hhKHApOnJldHVybiBoYXNobGliLnNoYTI1NihwLnJlYWRfYnl0ZXMoKSkuaGV4ZGlnZXN0KCkKZGVmIGRlbmllZChwLHJvb3Q9Tm9uZSk6CiB0cnk6cT1wLnJlbGF0aXZlX3RvKHJvb3QpIGlmIHJvb3QgaXMgbm90IE5vbmUgZWxzZSBwCiBleGNlcHQgVmFsdWVFcnJvcjpxPXAKIHJldHVybiBhbnkoeCBpbiBERU5ZX1BBUlRTIGZvciB4IGluIHEucGFydHMpIG9yIGFueShyLnNlYXJjaChxLm5hbWUpIGZvciByIGluIERFTllfUEFUVEVSTlMpClBSSVZBVEVfS0VZX0JMT0NLPXJlLmNvbXBpbGUoYnInLS0tLS1CRUdJTiBbQS1aIF0qUFJJVkFURSBLRVktLS0tLVxzKiguKj8pXHMqLS0tLS1FTkQgW0EtWiBdKlBSSVZBVEUgS0VZLS0tLS0nLHJlLkl8cmUuUykKQUxMT1dFRF9TWU5USEVUSUNfRklYVFVSRVM9eyd0ZXN0cy90ZXN0X3NlY3JldF9ibG9iX2hhcmRlbmluZy5weSd9CmRlZiByZWxhdGl2ZV9pZGVudGl0eShwLGN1cnJlbnQ9Tm9uZSk6CiBpZiBjdXJyZW50IGlzIG5vdCBOb25lOgogIHRyeTpyZXR1cm4gcC5yZWxhdGl2ZV90byhjdXJyZW50KS5hc19wb3NpeCgpCiAgZXhjZXB0IFZhbHVlRXJyb3I6cGFzcwogcmV0dXJuIHAuYXNfcG9zaXgoKQpkZWYgcmVhbF9wcml2YXRlX2tleV9tYXRlcmlhbChiKToKIGZvciBtYXRjaCBpbiBQUklWQVRFX0tFWV9CTE9DSy5maW5kaXRlcihiKToKICBib2R5PXJlLnN1YihicidbXkEtWmEtejAtOSsvPV0nLGInJyxtYXRjaC5ncm91cCgxKSkKICBpZiBsZW4oYm9keSk+PTEyODpyZXR1cm4gVHJ1ZQogcmV0dXJuIEZhbHNlCmRlZiBzY2FuX2J5dGVzKGlkZW50aXR5LGIpOgogZmluZGluZ3M9W107YWNjZXB0ZWQ9W10KIGZvciByIGluIFNFQ1JFVF9QQVRURVJOUzoKICBpZiBub3Qgci5zZWFyY2goYik6Y29udGludWUKICBwYXR0ZXJuPXIucGF0dGVybi5kZWNvZGUoKQogIGlmIHBhdHRlcm49PSdCRUdJTiBbQS1aIF0qUFJJVkFURSBLRVknIGFuZCBpZGVudGl0eSBpbiBBTExPV0VEX1NZTlRIRVRJQ19GSVhUVVJFUyBhbmQgbm90IHJlYWxfcHJpdmF0ZV9rZXlfbWF0ZXJpYWwoYik6CiAgIGFjY2VwdGVkLmFwcGVuZCh7J2ZpbGUnOmlkZW50aXR5LCdwYXR0ZXJuJzonUFJJVkFURV9LRVlfVEVTVF9GSVhUVVJFJywnY2xhc3NpZmljYXRpb24nOidTWU5USEVUSUNfTk9OX1NFQ1JFVCd9KQogIGVsc2U6ZmluZGluZ3MuYXBwZW5kKHBhdHRlcm4pCiByZXR1cm4gZmluZGluZ3MsYWNjZXB0ZWQKZGVmIHNjYW5fZmlsZShwLGN1cnJlbnQ9Tm9uZSk6cmV0dXJuIHNjYW5fYnl0ZXMocmVsYXRpdmVfaWRlbnRpdHkocCxjdXJyZW50KSxwLnJlYWRfYnl0ZXMoKSkKZGVmIHNlbGVjdGVkX3JlbGVhc2UoY3VycmVudCk6CiBvdXQ9W10KIGZvciBwIGluIGN1cnJlbnQuaXRlcmRpcigpOgogIGlmIHAuaXNfZmlsZSgpIGFuZCAocC5zdWZmaXg9PScucHknIG9yIHAubmFtZSBpbiBUT1BfRklMRVMgb3IgcmUuZnVsbG1hdGNoKHInVlxkK19cZCtfXGQrX1JFTEVBU0VfTk9URVNfKElEfEVOKVwubWQnLHAubmFtZSkpIGFuZCBub3QgZGVuaWVkKHAsY3VycmVudCk6b3V0LmFwcGVuZChwKQogZm9yIG5hbWUgaW4gVFJFRVM6CiAgZD1jdXJyZW50L25hbWUKICBpZiBkLmlzX2RpcigpOm91dCArPSBbcCBmb3IgcCBpbiBkLnJnbG9iKCcqJykgaWYgcC5pc19maWxlKCkgYW5kIG5vdCBkZW5pZWQocCxjdXJyZW50KV0KIHJldHVybiBvdXQKZGVmIHNlbGVjdGVkX21hbmFnZXIobWFuYWdlcik6cmV0dXJuIFttYW5hZ2VyL24gZm9yIG4gaW4gTUFOQUdFUl9GSUxFUyBpZiAobWFuYWdlci9uKS5pc19maWxlKCkgYW5kIG5vdCBkZW5pZWQobWFuYWdlci9uLG1hbmFnZXIpXQpkZWYgaW5zdGFsbF9zY3JpcHQoKToKIGxpbmVzPVsKICAnIyEvdXNyL2Jpbi9lbnYgcHl0aG9uMycsCiAgJ2Zyb20gcGF0aGxpYiBpbXBvcnQgUGF0aCcsCiAgJ2ltcG9ydCBhcmdwYXJzZSxvcyxzaHV0aWwsc3VicHJvY2VzcyxzeXMnLAogICJwPWFyZ3BhcnNlLkFyZ3VtZW50UGFyc2VyKCk7cC5hZGRfYXJndW1lbnQoJy0tcm9vdCcsZGVmYXVsdD0nfi9TT0MtQXV0b21hdGlvbicpO3AuYWRkX2FyZ3VtZW50KCctLXNraXAtZGVwZW5kZW5jaWVzJyxhY3Rpb249J3N0b3JlX3RydWUnLGhlbHA9YXJncGFyc2UuU1VQUFJFU1MpO2E9cC5wYXJzZV9hcmdzKCkiLAogICJyb290PVBhdGgoYS5yb290KS5leHBhbmR1c2VyKCkucmVzb2x2ZSgpO2Jhc2U9UGF0aChfX2ZpbGVfXykucmVzb2x2ZSgpLnBhcmVudCIsCiAgIihyb290LydyZWxlYXNlcycpLm1rZGlyKHBhcmVudHM9VHJ1ZSxleGlzdF9vaz1UcnVlKTsocm9vdC8nbWFuYWdlcicpLm1rZGlyKGV4aXN0X29rPVRydWUpOyhyb290LydzaGFyZWQnKS5ta2RpcihleGlzdF9vaz1UcnVlKSIsCiAgImZvciByZWwgaW4gKCdsb2dzJywnY29udHJvbCcsJ2F1ZGl0X2xvZ3MnLCd3b3JrZXJzJywnYmFja3VwcycpOihyb290LydzaGFyZWQnL3JlbCkubWtkaXIocGFyZW50cz1UcnVlLGV4aXN0X29rPVRydWUpIiwKICAidmVyPShiYXNlLydwYXlsb2FkL3JlbGVhc2UvVkVSU0lPTicpLnJlYWRfdGV4dChlbmNvZGluZz0ndXRmLTgnKS5zdHJpcCgpO2Rlc3Q9cm9vdC8ncmVsZWFzZXMnL3ZlciIsCiAgImlmIGRlc3QuZXhpc3RzKCk6cmFpc2UgU3lzdGVtRXhpdCgnVGFyZ2V0IHJlbGVhc2UgYWxyZWFkeSBleGlzdHM6ICcrc3RyKGRlc3QpKSIsCiAgInNodXRpbC5jb3B5dHJlZShiYXNlLydwYXlsb2FkL3JlbGVhc2UnLGRlc3QpO3NodXRpbC5jb3B5dHJlZShiYXNlLydwYXlsb2FkL21hbmFnZXInLHJvb3QvJ21hbmFnZXInLGRpcnNfZXhpc3Rfb2s9VHJ1ZSkiLAogICJjdXI9cm9vdC8nY3VycmVudCc7dG1wPXJvb3QvJy5jdXJyZW50Lm5ldyc7dG1wLnVubGluayhtaXNzaW5nX29rPVRydWUpO3RtcC5zeW1saW5rX3RvKGRlc3QpO3RtcC5yZXBsYWNlKGN1cikiLAogICJtYXJrZXI9cm9vdC8nLmluc3RhbGxhdGlvbi1yb290JzttYXJrZXIud3JpdGVfdGV4dChzdHIocm9vdCkrY2hyKDEwKSxlbmNvZGluZz0ndXRmLTgnKTtvcy5jaG1vZChtYXJrZXIsMG82MDApIiwKICAibGF1bmNoZXI9cm9vdC8nbWFuYWdlci9zb2MtdHVpJztvcy5jaG1vZChsYXVuY2hlciwwbzc1MCkgaWYgbGF1bmNoZXIuZXhpc3RzKCkgZWxzZSBOb25lIiwKICAidmVudj1yb290LycudmVudic7c3VicHJvY2Vzcy5ydW4oW3N5cy5leGVjdXRhYmxlLCctbScsJ3ZlbnYnLHN0cih2ZW52KV0sY2hlY2s9VHJ1ZSkiLAogICJpZiBub3QgYS5za2lwX2RlcGVuZGVuY2llczpzdWJwcm9jZXNzLnJ1bihbc3RyKHZlbnYvJ2Jpbi9waXAnKSwnaW5zdGFsbCcsJy1yJyxzdHIoZGVzdC8ncmVxdWlyZW1lbnRzLnR4dCcpXSxjaGVjaz1UcnVlKSIsCiAgInByaW50KCdJbnN0YWxsZWQnLHZlciwnYXQnLHJvb3QpO3ByaW50KCdMYXVuY2hlcjonLGxhdW5jaGVyKSIsCiBdCiByZXR1cm4gY2hyKDEwKS5qb2luKGxpbmVzKStjaHIoMTApCgpkZWYgY29tcGlsZV9nYXRlKHBhdGgsbGFiZWwpOgogd2l0aCB0ZW1wZmlsZS5OYW1lZFRlbXBvcmFyeUZpbGUocHJlZml4PSdzb2MtY29tcGlsZS0nLHN1ZmZpeD0nLnB5YycpIGFzIGNvbXBpbGVkOgogIGNvZGU9J2ltcG9ydCBweV9jb21waWxlLHN5cztweV9jb21waWxlLmNvbXBpbGUoc3lzLmFyZ3ZbMV0sY2ZpbGU9c3lzLmFyZ3ZbMl0sZG9yYWlzZT1UcnVlKScKICByZXN1bHQ9c3VicHJvY2Vzcy5ydW4oW3N5cy5leGVjdXRhYmxlLCctYycsY29kZSxzdHIocGF0aCksY29tcGlsZWQubmFtZV0sdGV4dD1UcnVlLGNhcHR1cmVfb3V0cHV0PVRydWUpCiBpZiByZXN1bHQucmV0dXJuY29kZSE9MDpyYWlzZSBTeXN0ZW1FeGl0KGYnQlVJTEQgQkxPQ0tFRDoge2xhYmVsfSBjb21waWxlIGZhaWxlZDoge3Jlc3VsdC5zdGRlcnIuc3RyaXAoKX0nKQoKZGVmIGluc3RhbGxhdGlvbl9zaW11bGF0aW9uKHN0YWdlKToKIGNvbXBpbGVfZ2F0ZShzdGFnZS8naW5zdGFsbC5weScsJ2dlbmVyYXRlZCBpbnN0YWxsLnB5JykKIHdpdGggdGVtcGZpbGUuVGVtcG9yYXJ5RGlyZWN0b3J5KHByZWZpeD0nc29jLWluc3RhbGwtc2ltdWxhdGlvbi0nKSBhcyB0ZDoKICBzaW1yb290PVBhdGgodGQpLydDdXN0b20gUm9vdCAtIFNPQyBUZXN0JwogIHJlc3VsdD1zdWJwcm9jZXNzLnJ1bihbc3lzLmV4ZWN1dGFibGUsc3RyKHN0YWdlLydpbnN0YWxsLnB5JyksJy0tcm9vdCcsc3RyKHNpbXJvb3QpLCctLXNraXAtZGVwZW5kZW5jaWVzJ10sdGV4dD1UcnVlLGNhcHR1cmVfb3V0cHV0PVRydWUsdGltZW91dD0xODApCiAgaWYgcmVzdWx0LnJldHVybmNvZGUhPTA6cmFpc2UgU3lzdGVtRXhpdCgnQlVJTEQgQkxPQ0tFRDogY3VzdG9tLXJvb3QgaW5zdGFsbGF0aW9uIHNpbXVsYXRpb24gZmFpbGVkOiAnKyhyZXN1bHQuc3Rkb3V0K3Jlc3VsdC5zdGRlcnIpLnN0cmlwKCkpCiAgcmVxdWlyZWQ9W3NpbXJvb3QvJy5pbnN0YWxsYXRpb24tcm9vdCcsc2ltcm9vdC8nY3VycmVudC9WRVJTSU9OJyxzaW1yb290LydtYW5hZ2VyL3NvYy10dWknLHNpbXJvb3QvJy52ZW52L2Jpbi9weXRob24nXQogIG1pc3Npbmc9W3N0cihwKSBmb3IgcCBpbiByZXF1aXJlZCBpZiBub3QgcC5leGlzdHMoKV0KICBpZiBtaXNzaW5nOnJhaXNlIFN5c3RlbUV4aXQoJ0JVSUxEIEJMT0NLRUQ6IHNpbXVsYXRpb24gbWlzc2luZzogJysnLCAnLmpvaW4obWlzc2luZykpCiAgaWYgKHNpbXJvb3QvJy5pbnN0YWxsYXRpb24tcm9vdCcpLnJlYWRfdGV4dChlbmNvZGluZz0ndXRmLTgnKS5zdHJpcCgpIT1zdHIoc2ltcm9vdC5yZXNvbHZlKCkpOnJhaXNlIFN5c3RlbUV4aXQoJ0JVSUxEIEJMT0NLRUQ6IGluc3RhbGxhdGlvbiByb290IG1ldGFkYXRhIG1pc21hdGNoJykKICBjb21waWxlX2dhdGUoc2ltcm9vdC8nbWFuYWdlci9zb2NfY29udHJvbF90dWkucHknLCdpbnN0YWxsZWQgTWFuYWdlci9UVUknKQogIGluc3RhbGxlZF90dWk9c2ltcm9vdC8nbWFuYWdlci9zb2NfY29udHJvbF90dWkucHknO29yaWdpbmFsPWluc3RhbGxlZF90dWkucmVhZF9ieXRlcygpCiAgaW5zdGFsbGVkX3R1aS53cml0ZV90ZXh0KCJpbXBvcnQgYXJncGFyc2UscGF0aGxpYlxucD1hcmdwYXJzZS5Bcmd1bWVudFBhcnNlcigpO3AuYWRkX2FyZ3VtZW50KCctLXJvb3QnLHJlcXVpcmVkPVRydWUpO2E9cC5wYXJzZV9hcmdzKCk7cHJpbnQocGF0aGxpYi5QYXRoKGEucm9vdCkucmVzb2x2ZSgpKVxuIixlbmNvZGluZz0ndXRmLTgnKQogIGNsZWFuX2Vudj1vcy5lbnZpcm9uLmNvcHkoKQogIGNsZWFuX2Vudi5wb3AoJ1NPQ19BVVRPTUFUSU9OX1JPT1QnLE5vbmUpO2NsZWFuX2Vudi5wb3AoJ1BZVEhPTlBBVEgnLE5vbmUpCiAgbGF1bmNoZXI9c3VicHJvY2Vzcy5ydW4oW3N0cihzaW1yb290LydtYW5hZ2VyL3NvYy10dWknKSwnLS1yb290JyxzdHIoc2ltcm9vdCldLHRleHQ9VHJ1ZSxjYXB0dXJlX291dHB1dD1UcnVlLHRpbWVvdXQ9NjAsZW52PWNsZWFuX2VudixzdGRpbj1zdWJwcm9jZXNzLkRFVk5VTEwpCiAgaW5zdGFsbGVkX3R1aS53cml0ZV9ieXRlcyhvcmlnaW5hbCkKICBpZiBsYXVuY2hlci5yZXR1cm5jb2RlIT0wIG9yIGxhdW5jaGVyLnN0ZG91dC5zdHJpcCgpIT1zdHIoc2ltcm9vdC5yZXNvbHZlKCkpOnJhaXNlIFN5c3RlbUV4aXQoJ0JVSUxEIEJMT0NLRUQ6IGN1c3RvbS1yb290IGxhdW5jaGVyIHRlc3QgZmFpbGVkOiAnKyhsYXVuY2hlci5zdGRvdXQrbGF1bmNoZXIuc3RkZXJyKS5zdHJpcCgpKQogcmV0dXJuIHsnZ2VuZXJhdGVkX2luc3RhbGxfY29tcGlsZSc6J1BBU1MnLCdjdXN0b21fcm9vdF9zaW11bGF0aW9uJzonUEFTUycsJ2xhdW5jaGVyX2V4ZWN1dGlvbic6J1BBU1MnLCdpbnN0YWxsZWRfdHVpX2NvbXBpbGUnOidQQVNTJywnaW5zdGFsbGF0aW9uX3Jvb3RfbWV0YWRhdGEnOidQQVNTJ30KCmRlZiBidWlsZChyb290LG91dCxyZXBvcnQpOgogY3VycmVudD0ocm9vdC8nY3VycmVudCcpLnJlc29sdmUoKTttYW5hZ2VyPXJvb3QvJ21hbmFnZXInO3ZlcnNpb249KGN1cnJlbnQvJ1ZFUlNJT04nKS5yZWFkX3RleHQoKS5zdHJpcCgpO2ZpbGVzPVtdCiB3aXRoIHRlbXBmaWxlLlRlbXBvcmFyeURpcmVjdG9yeShwcmVmaXg9J3NvYy1mdWxsLXNhZmUtJykgYXMgdGQ6CiAgc3RhZ2U9UGF0aCh0ZCkvZidTT0MtQXV0b21hdGlvbi12e3ZlcnNpb259LUZVTEwtSU5TVEFMTCc7KHN0YWdlLydwYXlsb2FkL3JlbGVhc2UnKS5ta2RpcihwYXJlbnRzPVRydWUpOyhzdGFnZS8ncGF5bG9hZC9tYW5hZ2VyJykubWtkaXIocGFyZW50cz1UcnVlKQogIGZvciBwIGluIHNlbGVjdGVkX3JlbGVhc2UoY3VycmVudCk6CiAgIHJlbD1wLnJlbGF0aXZlX3RvKGN1cnJlbnQpO3E9c3RhZ2UvJ3BheWxvYWQvcmVsZWFzZScvcmVsO3EucGFyZW50Lm1rZGlyKHBhcmVudHM9VHJ1ZSxleGlzdF9vaz1UcnVlKTtzaHV0aWwuY29weTIocCxxKTtmaWxlcy5hcHBlbmQocSkKICBmb3IgcCBpbiBzZWxlY3RlZF9tYW5hZ2VyKG1hbmFnZXIpOgogICBxPXN0YWdlLydwYXlsb2FkL21hbmFnZXInL3AubmFtZTtzaHV0aWwuY29weTIocCxxKTtmaWxlcy5hcHBlbmQocSkKICByZXF1aXJlZF9yZWxlYXNlPVsnVkVSU0lPTicsJ1JFTEVBU0UuanNvbicsJ3JlcXVpcmVtZW50cy50eHQnLCdtYWluLnB5JywnY29uZmlnLnB5J10KICBtaXNzaW5nPVtuYW1lIGZvciBuYW1lIGluIHJlcXVpcmVkX3JlbGVhc2UgaWYgbm90IChzdGFnZS8ncGF5bG9hZC9yZWxlYXNlJy9uYW1lKS5pc19maWxlKCldCiAgaWYgbWlzc2luZzpyYWlzZSBTeXN0ZW1FeGl0KCdCVUlMRCBCTE9DS0VEOiBtaXNzaW5nIHJlcXVpcmVkIHJlbGVhc2UgcGF5bG9hZDogJysnLCAnLmpvaW4obWlzc2luZykpCiAgcmVsZWFzZV9maWxlcz1bcCBmb3IgcCBpbiAoc3RhZ2UvJ3BheWxvYWQvcmVsZWFzZScpLnJnbG9iKCcqJykgaWYgcC5pc19maWxlKCldCiAgaWYgbGVuKHJlbGVhc2VfZmlsZXMpPDEwOnJhaXNlIFN5c3RlbUV4aXQoZidCVUlMRCBCTE9DS0VEOiByZWxlYXNlIHBheWxvYWQgdW5leHBlY3RlZGx5IHNtYWxsICh7bGVuKHJlbGVhc2VfZmlsZXMpfSBmaWxlcyknKQogIChzdGFnZS8naW5zdGFsbC5weScpLndyaXRlX3RleHQoaW5zdGFsbF9zY3JpcHQoKSxlbmNvZGluZz0ndXRmLTgnKTtvcy5jaG1vZChzdGFnZS8naW5zdGFsbC5weScsMG83NTUpCiAgaW5zdGFsbGVyX3ZhbGlkYXRpb249aW5zdGFsbGF0aW9uX3NpbXVsYXRpb24oc3RhZ2UpCiAgZW52PWN1cnJlbnQvJ2Vudi5leGFtcGxlJwogIGlmIGVudi5leGlzdHMoKTogKHN0YWdlLydjb25maWcnKS5ta2RpcigpO3NodXRpbC5jb3B5MihlbnYsc3RhZ2UvJ2NvbmZpZy9lbnYuZXhhbXBsZScpCiAgYmFkPVtdO2FjY2VwdGVkPVtdCiAgZm9yIHAgaW4gc3RhZ2Uucmdsb2IoJyonKToKICAgaWYgcC5pc19maWxlKCk6CiAgICBpZiBkZW5pZWQocCk6YmFkLmFwcGVuZCh7J2ZpbGUnOnN0cihwLnJlbGF0aXZlX3RvKHN0YWdlKSksJ3JlYXNvbic6J2RlbmllZF9uYW1lJ30pCiAgICBpZGVudGl0eT1zdHIocC5yZWxhdGl2ZV90byhzdGFnZSkpLnJlcGxhY2UoJ3BheWxvYWQvcmVsZWFzZS8nLCcnLDEpIGlmIHN0cihwLnJlbGF0aXZlX3RvKHN0YWdlKSkuc3RhcnRzd2l0aCgncGF5bG9hZC9yZWxlYXNlLycpIGVsc2Ugc3RyKHAucmVsYXRpdmVfdG8oc3RhZ2UpKQogICAgaGl0cyxhY2NlcHRlZF9oaXRzPXNjYW5fYnl0ZXMoaWRlbnRpdHkscC5yZWFkX2J5dGVzKCkpCiAgICBmb3IgaGl0IGluIGhpdHM6YmFkLmFwcGVuZCh7J2ZpbGUnOnN0cihwLnJlbGF0aXZlX3RvKHN0YWdlKSksJ3JlYXNvbic6J3NlY3JldF9wYXR0ZXJuJywncGF0dGVybic6aGl0fSkKICAgIGFjY2VwdGVkLmV4dGVuZChhY2NlcHRlZF9oaXRzKQogIGlmIGJhZDpyYWlzZSBTeXN0ZW1FeGl0KCdCVUlMRCBCTE9DS0VEOiAnK2pzb24uZHVtcHMoYmFkWzoyMF0pKQogIG1hbmlmZXN0PXsnc2NoZW1hX3ZlcnNpb24nOjIsJ2FwcGxpY2F0aW9uJzonU09DIEppcmEgQXV0b21hdGlvbiBGdWxsIEluc3RhbGxlcicsJ3ZlcnNpb24nOnZlcnNpb24sJ2J1aWxkZXJfcG9saWN5JzonZXhwbGljaXQtYWN0aXZlLWZpbGUtYWxsb3dsaXN0JywnY3JlYXRlZF9hdCc6ZGF0ZXRpbWUubm93KHRpbWV6b25lLnV0YykuaXNvZm9ybWF0KCksJ2ZpbGVzJzp7fX0KICBmb3IgcCBpbiBzb3J0ZWQoc3RhZ2Uucmdsb2IoJyonKSk6CiAgIGlmIHAuaXNfZmlsZSgpOm1hbmlmZXN0WydmaWxlcyddW3AucmVsYXRpdmVfdG8oc3RhZ2UpLmFzX3Bvc2l4KCldPXsnc2hhMjU2JzpzaGEocCksJ3NpemUnOnAuc3RhdCgpLnN0X3NpemV9CiAgKHN0YWdlLydtYW5pZmVzdC5qc29uJykud3JpdGVfdGV4dChqc29uLmR1bXBzKG1hbmlmZXN0LGluZGVudD0yKSk7CiAgc3Vtcz0nXG4nLmpvaW4oZiJ7c2hhKHApfSAge3AucmVsYXRpdmVfdG8oc3RhZ2UpLmFzX3Bvc2l4KCl9IiBmb3IgcCBpbiBzb3J0ZWQoc3RhZ2Uucmdsb2IoJyonKSkgaWYgcC5pc19maWxlKCkpKydcbic7KHN0YWdlLydTSEEyNTZTVU1TJykud3JpdGVfdGV4dChzdW1zKQogIG91dC5ta2RpcihwYXJlbnRzPVRydWUsZXhpc3Rfb2s9VHJ1ZSk7ej1vdXQvZidTT0MtQXV0b21hdGlvbi12e3ZlcnNpb259LUZVTEwtSU5TVEFMTC56aXAnCiAgd2l0aCB6aXBmaWxlLlppcEZpbGUoeiwndycsemlwZmlsZS5aSVBfREVGTEFURUQpIGFzIGE6CiAgIGZvciBwIGluIHNvcnRlZChzdGFnZS5yZ2xvYignKicpKToKICAgIGlmIHAuaXNfZmlsZSgpOmEud3JpdGUocCwoc3RhZ2UubmFtZSsnLycrcC5yZWxhdGl2ZV90byhzdGFnZSkuYXNfcG9zaXgoKSkpCiAgd2l0aCB6aXBmaWxlLlppcEZpbGUoeikgYXMgYToKICAgaWYgYS50ZXN0emlwKCk6cmFpc2UgU3lzdGVtRXhpdCgnWklQIGludGVncml0eSBmYWlsZWQnKQogIHdpdGggdGVtcGZpbGUuVGVtcG9yYXJ5RGlyZWN0b3J5KHByZWZpeD0nc29jLWluc3RhbGxlci1leHRyYWN0LWNoZWNrLScpIGFzIGV4dHJhY3RlZDoKICAgZXh0cmFjdF9yb290PVBhdGgoZXh0cmFjdGVkKQogICB3aXRoIHppcGZpbGUuWmlwRmlsZSh6KSBhcyBhcmNoaXZlOmFyY2hpdmUuZXh0cmFjdGFsbChleHRyYWN0X3Jvb3QpCiAgIHBhY2thZ2Vfcm9vdD1leHRyYWN0X3Jvb3Qvc3RhZ2UubmFtZQogICBjb21waWxlX2dhdGUocGFja2FnZV9yb290LydpbnN0YWxsLnB5JywnZXh0cmFjdGVkIGluc3RhbGwucHknKQogICBzdW1zPXt9CiAgIGZvciBsaW5lIGluIChwYWNrYWdlX3Jvb3QvJ1NIQTI1NlNVTVMnKS5yZWFkX3RleHQoZW5jb2Rpbmc9J3V0Zi04Jykuc3BsaXRsaW5lcygpOgogICAgZGlnZXN0X3ZhbHVlLHJlbGF0aXZlPWxpbmUuc3BsaXQoJyAgJywxKTtzdW1zW3JlbGF0aXZlXT1kaWdlc3RfdmFsdWUKICAgY2hlY2tzdW1fZmFpbHVyZXM9W25hbWUgZm9yIG5hbWUsZXhwZWN0ZWQgaW4gc3Vtcy5pdGVtcygpIGlmIG5vdCAocGFja2FnZV9yb290L25hbWUpLmlzX2ZpbGUoKSBvciBzaGEocGFja2FnZV9yb290L25hbWUpIT1leHBlY3RlZF0KICAgaWYgY2hlY2tzdW1fZmFpbHVyZXM6cmFpc2UgU3lzdGVtRXhpdCgnQlVJTEQgQkxPQ0tFRDogZXh0cmFjdGVkIGludGVybmFsIGNoZWNrc3VtIGZhaWx1cmU6ICcrJywgJy5qb2luKGNoZWNrc3VtX2ZhaWx1cmVzWzoyMF0pKQogIGluc3RhbGxlcl92YWxpZGF0aW9uWydleHRyYWN0ZWRfaW5zdGFsbF9jb21waWxlJ109J1BBU1MnO2luc3RhbGxlcl92YWxpZGF0aW9uWydpbnRlcm5hbF9jaGVja3N1bXMnXT0nUEFTUycKICBkaWdlc3Q9c2hhKHopOyhvdXQvKHoubmFtZSsnLnNoYTI1NicpKS53cml0ZV90ZXh0KGYne2RpZ2VzdH0gIHt6Lm5hbWV9XG4nKQogIHJlc3VsdD17J3N0YXR1cyc6J1BBU1MnLCd2ZXJzaW9uJzp2ZXJzaW9uLCdwYWNrYWdlJzpzdHIoeiksJ3NoYTI1Nic6ZGlnZXN0LCdmaWxlX2NvdW50JzpsZW4obWFuaWZlc3RbJ2ZpbGVzJ10pLCdleGNsdWRlZF9wYXR0ZXJucyc6WycqLmJhayonLCcqLnByZS0qJywnKi5iZWZvcmUtKicsJyouYnJva2VuLSonLCdzZWNyZXRzJywncHJvZHVjdGlvbiBzdGF0ZSddLCdwb2xpY3knOidleHBsaWNpdCBhY3RpdmUtZmlsZSBhbGxvd2xpc3QnLCdjdXN0b21fcm9vdF9sYXVuY2hlcic6J3Jvb3QtYXdhcmUnLCdpbnN0YWxsYXRpb25fcm9vdF9tZXRhZGF0YSc6Jy5pbnN0YWxsYXRpb24tcm9vdCcsJ2J1aWxkZXJfdmVyc2lvbic6JzEuMjcuMTEnLCdjdW11bGF0aXZlX2Zyb20nOlsnMS4yNy44JywnMS4yNy45JywnMS4yNy4xMCddLCdpbnN0YWxsZXJfZ2VuZXJhdGlvbl9tYXJrZXInOidpbnN0YWxsZXItZ2VuZXJhdGlvbi12MS4yNy4xMScsJ2luc3RhbGxlcl92YWxpZGF0aW9uJzppbnN0YWxsZXJfdmFsaWRhdGlvbn0KICByZXBvcnQucGFyZW50Lm1rZGlyKHBhcmVudHM9VHJ1ZSxleGlzdF9vaz1UcnVlKTtyZXBvcnQud3JpdGVfdGV4dChqc29uLmR1bXBzKHJlc3VsdCxpbmRlbnQ9MikpO3ByaW50KGpzb24uZHVtcHMocmVzdWx0LGluZGVudD0yKSkKZGVmIHNjYW5fcGtnKHAscmVwb3J0KToKIGJhZD1bXTthY2NlcHRlZD1bXQogd2l0aCB6aXBmaWxlLlppcEZpbGUocCkgYXMgejoKICBpZiB6LnRlc3R6aXAoKTpiYWQuYXBwZW5kKHsncmVhc29uJzonemlwX2ludGVncml0eSd9KQogIGZvciBuIGluIHoubmFtZWxpc3QoKToKICAgcT1QYXRoKG4pCiAgIGlmIGRlbmllZChxKTpiYWQuYXBwZW5kKHsnZmlsZSc6biwncmVhc29uJzonZGVuaWVkX25hbWUnfSkKICAgYj16LnJlYWQobikKICAgaWRlbnRpdHk9bi5zcGxpdCgnL3BheWxvYWQvcmVsZWFzZS8nLDEpWy0xXSBpZiAnL3BheWxvYWQvcmVsZWFzZS8nIGluIG4gZWxzZSBuCiAgIGhpdHMsYWNjZXB0ZWRfaGl0cz1zY2FuX2J5dGVzKGlkZW50aXR5LGIpCiAgIGZvciBoaXQgaW4gaGl0czpiYWQuYXBwZW5kKHsnZmlsZSc6biwncmVhc29uJzonc2VjcmV0X3BhdHRlcm4nLCdwYXR0ZXJuJzpoaXR9KQogICBhY2NlcHRlZC5leHRlbmQoYWNjZXB0ZWRfaGl0cykKIHJlc3VsdD17J3N0YXR1cyc6J1BBU1MnIGlmIG5vdCBiYWQgZWxzZSAnRkFJTCcsJ3BhY2thZ2UnOnN0cihwKSwnZmluZGluZ3MnOmJhZCwnYWNjZXB0ZWRfdGVzdF9maXh0dXJlcyc6YWNjZXB0ZWR9O3JlcG9ydC53cml0ZV90ZXh0KGpzb24uZHVtcHMocmVzdWx0LGluZGVudD0yKSk7cHJpbnQoanNvbi5kdW1wcyhyZXN1bHQsaW5kZW50PTIpKTtyYWlzZSBTeXN0ZW1FeGl0KDAgaWYgbm90IGJhZCBlbHNlIDIpCmRlZiBzY2FuX2FjdGl2ZV9yb290KHJvb3QscmVwb3J0KToKIGN1cnJlbnQ9KHJvb3QvJ2N1cnJlbnQnKS5yZXNvbHZlKCk7bWFuYWdlcj1yb290LydtYW5hZ2VyJztiYWQ9W107YWNjZXB0ZWQ9W107c2Nhbm5lZD1bXQogY2FuZGlkYXRlcz1zZWxlY3RlZF9yZWxlYXNlKGN1cnJlbnQpK3NlbGVjdGVkX21hbmFnZXIobWFuYWdlcikKIGZvciBwIGluIGNhbmRpZGF0ZXM6CiAgc2Nhbm5lZC5hcHBlbmQoc3RyKHApKQogIGlmIGRlbmllZChwLGN1cnJlbnQgaWYgcC5pc19yZWxhdGl2ZV90byhjdXJyZW50KSBlbHNlIG1hbmFnZXIpOmJhZC5hcHBlbmQoeydmaWxlJzpzdHIocCksJ3JlYXNvbic6J2RlbmllZF9uYW1lJ30pCiAgaGl0cyxhY2NlcHRlZF9oaXRzPXNjYW5fZmlsZShwLGN1cnJlbnQgaWYgcC5pc19yZWxhdGl2ZV90byhjdXJyZW50KSBlbHNlIG1hbmFnZXIpCiAgZm9yIGhpdCBpbiBoaXRzOmJhZC5hcHBlbmQoeydmaWxlJzpzdHIocCksJ3JlYXNvbic6J3NlY3JldF9wYXR0ZXJuJywncGF0dGVybic6aGl0fSkKICBhY2NlcHRlZC5leHRlbmQoYWNjZXB0ZWRfaGl0cykKIHJlc3VsdD17J3N0YXR1cyc6J1BBU1MnIGlmIG5vdCBiYWQgZWxzZSAnRkFJTCcsJ21vZGUnOidhY3RpdmVfYWxsb3dsaXN0ZWRfc291cmNlX3NjYW4nLCdzY2FubmVkX2ZpbGVfY291bnQnOmxlbihzY2FubmVkKSwnZmluZGluZ3MnOmJhZCwnYWNjZXB0ZWRfdGVzdF9maXh0dXJlcyc6YWNjZXB0ZWQsJ3BvbGljeSc6J2V4cGxpY2l0IGFjdGl2ZS1maWxlIGFsbG93bGlzdCArIGZpeHR1cmUtYXdhcmUgc2VjcmV0IHZhbGlkYXRpb24nfQogcmVwb3J0LnBhcmVudC5ta2RpcihwYXJlbnRzPVRydWUsZXhpc3Rfb2s9VHJ1ZSk7cmVwb3J0LndyaXRlX3RleHQoanNvbi5kdW1wcyhyZXN1bHQsaW5kZW50PTIpKTtwcmludChqc29uLmR1bXBzKHJlc3VsdCxpbmRlbnQ9MikpO3JhaXNlIFN5c3RlbUV4aXQoMCBpZiBub3QgYmFkIGVsc2UgMikKZGVmIG1haW4oKToKIGE9YXJncGFyc2UuQXJndW1lbnRQYXJzZXIoKTthLmFkZF9hcmd1bWVudCgnLS1yb290JyxkZWZhdWx0PSd+L1NPQy1BdXRvbWF0aW9uJyk7YS5hZGRfYXJndW1lbnQoJy0tb3V0cHV0Jyk7YS5hZGRfYXJndW1lbnQoJy0tcmVwb3J0JyxkZWZhdWx0PSdpbnN0YWxsZXItc2Nhbi1yZXBvcnQuanNvbicpO2EuYWRkX2FyZ3VtZW50KCctLXNjYW4tcGFja2FnZScpO2EuYWRkX2FyZ3VtZW50KCctLXNjYW4tb25seScsYWN0aW9uPSdzdG9yZV90cnVlJyk7eD1hLnBhcnNlX2FyZ3MoKTtyZXBvcnQ9UGF0aCh4LnJlcG9ydCkuZXhwYW5kdXNlcigpLnJlc29sdmUoKQogaWYgeC5zY2FuX3BhY2thZ2U6cmV0dXJuIHNjYW5fcGtnKFBhdGgoeC5zY2FuX3BhY2thZ2UpLmV4cGFuZHVzZXIoKS5yZXNvbHZlKCkscmVwb3J0KQogaWYgeC5zY2FuX29ubHk6cmV0dXJuIHNjYW5fYWN0aXZlX3Jvb3QoUGF0aCh4LnJvb3QpLmV4cGFuZHVzZXIoKS5yZXNvbHZlKCkscmVwb3J0KQogaWYgbm90IHgub3V0cHV0OnJhaXNlIFN5c3RlbUV4aXQoJy0tb3V0cHV0IHJlcXVpcmVkJykKIGJ1aWxkKFBhdGgoeC5yb290KS5leHBhbmR1c2VyKCkucmVzb2x2ZSgpLFBhdGgoeC5vdXRwdXQpLmV4cGFuZHVzZXIoKS5yZXNvbHZlKCkscmVwb3J0KQppZiBfX25hbWVfXz09J19fbWFpbl9fJzptYWluKCkK'
ROOT_AWARE_LAUNCHER_B64='IyEvYmluL3NoCnNldCAtZXUKCiMgc29jLXJvb3QtYXdhcmUtbGF1bmNoZXItdjEKU0NSSVBUX0RJUj0kKENEUEFUSD0gY2QgLS0gIiQoZGlybmFtZSAtLSAiJDAiKSIgJiYgcHdkIC1QKQpERVJJVkVEX1JPT1Q9JChDRFBBVEg9IGNkIC0tICIkU0NSSVBUX0RJUi8uLiIgJiYgcHdkIC1QKQpFWFBMSUNJVF9ST09UPSIiClBSRVY9IiIKZm9yIEFSRyBpbiAiJEAiOyBkbwogICAgaWYgWyAiJFBSRVYiID0gIi0tcm9vdCIgXTsgdGhlbgogICAgICAgIEVYUExJQ0lUX1JPT1Q9JEFSRwogICAgICAgIGJyZWFrCiAgICBmaQogICAgUFJFVj0kQVJHCmRvbmUKaWYgWyAtbiAiJEVYUExJQ0lUX1JPT1QiIF07IHRoZW4KICAgIFJPT1Q9JEVYUExJQ0lUX1JPT1QKZWxpZiBbIC1uICIke1NPQ19BVVRPTUFUSU9OX1JPT1Q6LX0iIF07IHRoZW4KICAgIFJPT1Q9JFNPQ19BVVRPTUFUSU9OX1JPT1QKZWxpZiBbIC1mICIkREVSSVZFRF9ST09ULy5pbnN0YWxsYXRpb24tcm9vdCIgXTsgdGhlbgogICAgUk9PVD0kKGNhdCAiJERFUklWRURfUk9PVC8uaW5zdGFsbGF0aW9uLXJvb3QiKQplbHNlCiAgICBST09UPSRERVJJVkVEX1JPT1QKZmkKUk9PVD0kKENEUEFUSD0gY2QgLS0gIiRST09UIiAyPi9kZXYvbnVsbCAmJiBwd2QgLVApIHx8IHsKICAgIGVjaG8gIkVSUk9SOiBJbnN0YWxsYXRpb24gcm9vdCB0aWRhayB2YWxpZDogJFJPT1QiID4mMgogICAgZXhpdCAxCn0KUFlUSE9OPSIkUk9PVC8udmVudi9iaW4vcHl0aG9uIgpUVUk9IiRST09UL21hbmFnZXIvc29jX2NvbnRyb2xfdHVpLnB5IgpDVVJSRU5UPSIkUk9PVC9jdXJyZW50IgppZiBbICEgLXggIiRQWVRIT04iIF07IHRoZW4KICAgIGVjaG8gIkVSUk9SOiBQeXRob24gdmlydHVhbCBlbnZpcm9ubWVudCB0aWRhayBkaXRlbXVrYW4uIiA+JjIKICAgIGVjaG8gIkVmZmVjdGl2ZSByb290OiAkUk9PVCIgPiYyCiAgICBlY2hvICJFeHBlY3RlZDogJFBZVEhPTiIgPiYyCiAgICBleGl0IDEKZmkKaWYgWyAhIC1mICIkVFVJIiBdOyB0aGVuCiAgICBlY2hvICJFUlJPUjogVFVJIG1hbmFnZXIgdGlkYWsgZGl0ZW11a2FuLiIgPiYyCiAgICBlY2hvICJFZmZlY3RpdmUgcm9vdDogJFJPT1QiID4mMgogICAgZWNobyAiRXhwZWN0ZWQ6ICRUVUkiID4mMgogICAgZXhpdCAxCmZpCmlmIFsgISAtZSAiJENVUlJFTlQiIF0gfHwgWyAhIC1mICIkQ1VSUkVOVC9WRVJTSU9OIiBdOyB0aGVuCiAgICBlY2hvICJFUlJPUjogQWN0aXZlIHJlbGVhc2UgdGlkYWsgdmFsaWQuIiA+JjIKICAgIGVjaG8gIkVmZmVjdGl2ZSByb290OiAkUk9PVCIgPiYyCiAgICBlY2hvICJFeHBlY3RlZDogJENVUlJFTlQvVkVSU0lPTiIgPiYyCiAgICBleGl0IDEKZmkKZXhwb3J0IFNPQ19BVVRPTUFUSU9OX1JPT1Q9IiRST09UIgpleHBvcnQgUFlUSE9OUEFUSD0iJFJPT1QvY3VycmVudDokUk9PVC9tYW5hZ2VyJHtQWVRIT05QQVRIOis6JFBZVEhPTlBBVEh9IgpjYXNlICIgJCogIiBpbgogICoiIC0tcm9vdCAiKikgZXhlYyAiJFBZVEhPTiIgIiRUVUkiICIkQCIgOzsKICAqKSBleGVjICIkUFlUSE9OIiAiJFRVSSIgLS1yb290ICIkUk9PVCIgIiRAIiA7Owplc2FjCg=='
PORTABILITY_MARKER='cumulative-installer-generation-v1.27.11'

class TUI:
 def __init__(self,s,root):
  self.s=s; self.root=root.expanduser().resolve(); self.current=self.root/'current'; self.manager=self.root/'manager'; self.shared=self.root/'shared'; self.logs=self.shared/'logs'; self.backups=self.shared/'backups'; self.activity=self.logs/'tui_activity.jsonl'
  self.logs.mkdir(parents=True,exist_ok=True); self.backups.mkdir(parents=True,exist_ok=True); self.ensure_portability_fix(); curses.curs_set(0); s.keypad(True)
  if curses.has_colors():
   curses.start_color(); curses.use_default_colors()
   for n,fg,bg in [(1,curses.COLOR_CYAN,-1),(2,curses.COLOR_GREEN,-1),(3,curses.COLOR_YELLOW,-1),(4,curses.COLOR_RED,-1),(5,curses.COLOR_WHITE,curses.COLOR_BLUE),(6,curses.COLOR_MAGENTA,-1),(7,curses.COLOR_WHITE,-1)]: curses.init_pair(n,fg,bg)
 def ensure_portability_fix(self):
  import base64
  self.manager.mkdir(parents=True,exist_ok=True)
  launcher=self.manager/'soc-tui';builder=self.manager/'build_full_local_installer.py'
  launcher_data=base64.b64decode(ROOT_AWARE_LAUNCHER_B64)
  builder_data=base64.b64decode(ROOT_AWARE_BUILDER_B64)
  if not launcher.is_file() or b'soc-root-aware-launcher-v1' not in launcher.read_bytes():
   tmp=launcher.with_name('.soc-tui.new');tmp.write_bytes(launcher_data);os.chmod(tmp,0o750);os.replace(tmp,launcher)
  if not builder.is_file() or b'installer-generation-v1.27.11' not in builder.read_bytes():
   tmp=builder.with_name('.build_full_local_installer.py.new');tmp.write_bytes(builder_data);os.chmod(tmp,0o700);subprocess.run([sys.executable,'-m','py_compile',str(tmp)],check=True,capture_output=True,text=True);os.replace(tmp,builder)
  marker=self.root/'.installation-root'
  if not marker.exists():marker.write_text(str(self.root)+'\n');os.chmod(marker,0o600)
  self.update_portability_docs()
 def update_portability_docs(self):
  entries={
   'docs/id/installation.md':'## Manager/TUI v1.27.10 - Instalasi custom root\n\nPatch cumulative v1.27.10 dapat dipasang langsung dari v1.27.8 atau v1.27.9. Installer menggunakan `chr(10)` untuk metadata root dan memvalidasi generated `install.py` sebelum distribusi.\n',
   'docs/en/installation.md':'## Manager/TUI v1.27.10 - Custom-root installation\n\nCumulative patch v1.27.10 can be installed directly from v1.27.8 or v1.27.9. The installer uses `chr(10)` for root metadata and validates generated `install.py` before distribution.\n',
   'docs/id/update-backup-rollback.md':'## Jalur upgrade Manager/TUI v1.27.10\n\nDidukung langsung: v1.27.8 ke v1.27.10 dan v1.27.9 ke v1.27.10. Instalasi v1.27.9 tidak diwajibkan.\n',
   'docs/en/update-backup-rollback.md':'## Manager/TUI v1.27.10 upgrade path\n\nDirect upgrades are supported from v1.27.8 and v1.27.9. Installing v1.27.9 first is not required.\n',
   'docs/id/troubleshooting.md':'## Generated install.py syntax error\n\nMasalah newline bertingkat pada v1.27.9 diselesaikan oleh v1.27.10. Build sekarang fail-closed pada compile, extraction, checksum, custom-root simulation, dan launcher gate.\n',
   'docs/en/troubleshooting.md':'## Generated install.py syntax error\n\nThe nested-newline defect in v1.27.9 is resolved by v1.27.10. Builds now fail closed on compile, extraction, checksum, custom-root simulation, and launcher gates.\n',
   'docs/id/known-issues.md':'## v1.27.9 superseded\n\nv1.27.9 adalah internal superseded build dan tidak boleh digunakan untuk menghasilkan Full Installer. Gunakan cumulative v1.27.10.\n',
   'docs/en/known-issues.md':'## v1.27.9 superseded\n\nv1.27.9 is a superseded internal build and must not be used for Full Installer generation. Use cumulative v1.27.10.\n',
   'docs/id/validation.md':'## Gate installer v1.27.10\n\nWajib PASS: generated compile, custom-root simulation, launcher execution, extracted compile, internal checksum, ZIP integrity, secret scan, dan production-state exclusion.\n',
   'docs/en/validation.md':'## v1.27.10 installer gates\n\nRequired PASS: generated compile, custom-root simulation, launcher execution, extracted compile, internal checksums, ZIP integrity, secret scan, and production-state exclusion.\n',
   'docs/id/version-history.md':'## Manager/TUI v1.27.10 - Cumulative Installer Generation Fix\n\nDirekomendasikan untuk instalasi existing. Mendukung upgrade langsung dari v1.27.8 dan v1.27.9. v1.27.9 ditandai superseded.\n',
   'docs/en/version-history.md':'## Manager/TUI v1.27.10 - Cumulative Installer Generation Fix\n\nRecommended for existing installations. Supports direct upgrades from v1.27.8 and v1.27.9. v1.27.9 is marked superseded.\n',
   'docs/id/version-history-v1.27.11.md':'## Manager/TUI v1.27.11 - Isolated Launcher Validation Fix\n\nMemperbaiki acceptance test launcher agar menghapus inherited `SOC_AUTOMATION_ROOT` dan `PYTHONPATH`, menggunakan explicit custom `--root`, dan tidak membuka curses TUI pada non-interactive build subprocess. Upgrade cumulative didukung dari v1.27.8, v1.27.9, dan v1.27.10.\n',
   'docs/en/version-history-v1.27.11.md':'## Manager/TUI v1.27.11 - Isolated Launcher Validation Fix\n\nFixes launcher acceptance by removing inherited `SOC_AUTOMATION_ROOT` and `PYTHONPATH`, using an explicit custom `--root`, and preventing the curses TUI from opening in a non-interactive build subprocess. Cumulative upgrades are supported from v1.27.8, v1.27.9, and v1.27.10.\n'
  }
  for rel,body in entries.items():
   path=self.current/rel
   if path.is_file() and PORTABILITY_MARKER not in path.read_text(encoding='utf-8',errors='replace'):
    with path.open('a',encoding='utf-8') as handle:handle.write('\n<!-- '+PORTABILITY_MARKER+' -->\n'+body)
 def c(self,n): return curses.color_pair(n) if curses.has_colors() else 0
 def getkey(self):
  key=self.s.getch()
  if key==curses.KEY_RESIZE:
   try:
    curses.update_lines_cols()
    self.s.clear()
    self.s.erase()
    self.s.refresh()
   except curses.error:
    pass
  return key
 def separator(self,y):
  h,w=self.s.getmaxyx()
  if y < 0 or y >= h or w < 3:return
  width=max(1,w-2)
  try:
   self.s.addnstr(y,1,chr(0x2500)*width,width)
  except (curses.error,UnicodeError):
   try:self.s.addnstr(y,1,'-'*width,width)
   except curses.error:pass
 def log(self,action,status='ok',details=None):
  rec={'time':dt.datetime.now().astimezone().isoformat(),'user':os.getenv('USER','unknown'),'pid':os.getpid(),'action':action,'status':status,'details':details or {}}
  with self.activity.open('a',encoding='utf-8') as f:f.write(json.dumps(rec,ensure_ascii=False)+'\n')
  os.chmod(self.activity,0o600)
 def frame(self,title,sub=''):
  self.s.erase()
  h,w=self.s.getmaxyx()
  if h<24 or w<80:
   message=(
    f'Terminal terlalu kecil: {w}x{h}. '
    'Perbesar terminal minimal menjadi 80x24.'
   )
   try:
    self.s.addnstr(
     0,0,message,max(1,w-1),
     self.c(3)|curses.A_BOLD,
    )
    self.s.addnstr(
     2,0,
     'TUI akan menyesuaikan otomatis setelah resize.',
     max(1,w-1),
    )
    self.s.refresh()
   except curses.error:
    pass
   return h,w
  try:
   self.s.addnstr(
    0,0,f' {TITLE} '.center(w),
    max(1,w-1),
    self.c(5)|curses.A_BOLD,
   )
   self.s.addnstr(
    1,2,title,max(1,w-4),
    self.c(1)|curses.A_BOLD,
   )
   if sub:
    self.s.addnstr(
     2,2,sub,max(1,w-4),self.c(6),
    )
  except curses.error:
   pass
  self.separator(3)
  return h,w
 def foot(self,msg='Enter: select | B: back | Q: quit'):
  h,w=self.s.getmaxyx(); self.separator(h-2); self.s.addnstr(h-1,2,msg,max(1,w-4),self.c(3)); self.s.refresh()
 def menu(self,title,items,sub=''):
  p=0
  while 1:
   h,w=self.frame(title,sub)
   for i,(label,_) in enumerate(items): self.s.addnstr(5+i,3,('▶ ' if i==p else '  ')+label,w-6,(self.c(5)|curses.A_BOLD) if i==p else self.c(1))
   self.foot(); k=self.getkey()
   if k in (ord('b'),ord('B'),ord('q'),ord('Q'),27):return
   if k in (curses.KEY_DOWN,ord('j')):p=(p+1)%len(items)
   elif k in (curses.KEY_UP,ord('k')):p=(p-1)%len(items)
   elif k in (10,13,curses.KEY_ENTER):items[p][1]()
 def text(self,title,data):
  raw_lines=str(data).splitlines() or ['']
  p=0
  previous_width=None
  lines=[]
  while 1:
   h,w=self.frame(title)
   wrap_width=max(20,w-6)
   if previous_width!=wrap_width:
    lines=[]
    for raw in raw_lines:
     wrapped=textwrap.wrap(
      raw,
      wrap_width,
      replace_whitespace=False,
      drop_whitespace=False,
     )
     lines.extend(wrapped or [''])
    previous_width=wrap_width
    p=min(p,max(0,len(lines)-1))
   vis=max(1,h-6)
   max_offset=max(0,len(lines)-vis)
   p=min(p,max_offset)
   subtitle=(
    f'Lines {p+1}-'
    f'{min(len(lines),p+vis)} / {len(lines)}'
   )
   self.s.addnstr(
    2,2,subtitle,max(1,w-4),self.c(6)
   )
   for y,line in enumerate(lines[p:p+vis],4):
    if y>=h-2:break
    try:self.s.addnstr(y,2,line,max(1,w-4))
    except curses.error:pass
   self.foot(
    'Up/Down/PgUp/PgDn: scroll | B/Q: back'
   )
   k=self.getkey()
   if k in (
    ord('b'),ord('B'),ord('q'),ord('Q'),27
   ):return
   if k==curses.KEY_RESIZE:
    continue
   if k in (curses.KEY_DOWN,ord('j')):
    p=min(max_offset,p+1)
   elif k in (curses.KEY_UP,ord('k')):
    p=max(0,p-1)
   elif k==curses.KEY_NPAGE:
    p=min(max_offset,p+vis)
   elif k==curses.KEY_PPAGE:
    p=max(0,p-vis)
 def _safe_add(self,y,x,text,attr=0):
  h,w=self.s.getmaxyx()
  if y<0 or y>=h or x<0 or x>=w:return
  try:self.s.addnstr(y,x,str(text).replace('\t','    '),max(0,w-x-1),attr)
  except curses.error:pass
 def _draw_form(self,title,lines=()):
  self.s.erase();h,w=self.s.getmaxyx();self._safe_add(0,max(1,(w-26)//2),'SOC AUTOMATION CONTROL TUI',curses.A_BOLD|self.c(5));self._safe_add(1,2,title,self.c(6));row=3
  for line in lines:self._safe_add(row,2,line,self.c(7));row+=1
  if row<h-2:self._safe_add(row,1,'-'*max(1,w-3),curses.A_DIM)
  self.s.refresh();return row+2
 def choose(self,title,options,subtitle='Use Up/Down and Enter'):
  if not options:return None
  idx=0;offset=0
  while True:
   h,w=self.s.getmaxyx();first=self._draw_form(title,str(subtitle).splitlines());available=max(1,h-first-2)
   if idx<offset:offset=idx
   if idx>=offset+available:offset=idx-available+1
   for n,opt in enumerate(options[offset:offset+available]):
    absolute=offset+n;prefix='> ' if absolute==idx else '  ';attr=curses.A_REVERSE|curses.A_BOLD if absolute==idx else self.c(1);self._safe_add(first+n,2,prefix+str(opt),attr)
   self._safe_add(h-1,2,'Up/Down: select | Enter: confirm | B/Q/Esc: cancel',self.c(3));self.s.refresh();key=self.s.getch()
   if key in (curses.KEY_UP,ord('k')):idx=(idx-1)%len(options)
   elif key in (curses.KEY_DOWN,ord('j')):idx=(idx+1)%len(options)
   elif key in (10,13,curses.KEY_ENTER):return options[idx]
   elif key in (27,ord('b'),ord('B'),ord('q'),ord('Q')):return None
 def confirm_choice(self,title,msg):return self.choose(title,['No','Yes'],msg)=='Yes'
 def _edit_value(self,title,prompt,default='',secret=False):
  value=list(str(default or ''))
  while True:
   h,w=self.s.getmaxyx();first=self._draw_form(title,[prompt,'','Input:']);maxlen=max(1,w-8);shown=('*'*len(value) if secret else ''.join(value))[-maxlen:];self._safe_add(first,4,shown or ' ',curses.A_REVERSE);self._safe_add(h-1,2,'Enter: submit | Ctrl+U: clear | Esc: cancel',self.c(3));self.s.move(min(first,h-2),min(4+len(shown),w-2));self.s.refresh();k=self.s.get_wch()
   if k in ('\n','\r'):return ''.join(value)
   if k=='\x1b':return ''
   if k=='\x15':value=[];continue
   if k in ('\b','\x7f') or k==curses.KEY_BACKSPACE:
    if value:value.pop()
   elif isinstance(k,str) and k.isprintable():value.append(k)
 def ask(self,title,prompt,default=''):return self._edit_value(title,prompt,default,False)
 def ask_secret(self,title,prompt):return self._edit_value(title,prompt,'',True)
 def yes(self,title,msg):
  return self.choose(title,['No','Yes'],msg)=='Yes'
 def cmd(self,title,args,timeout=900):
  self.log('command',details={'args':args}); self.frame(title,'Executing...'); self.s.refresh()
  try:r=subprocess.run(args,text=True,capture_output=True,timeout=timeout); self.log(title,'ok' if r.returncode==0 else 'failed',{'returncode':r.returncode}); self.text(title,(r.stdout+'\n'+r.stderr).strip() or '(no output)'); return r.returncode==0
  except Exception as e:self.log(title,'error',{'error':str(e)}); self.text(title,f'ERROR: {e}'); return False
 def read(self,p):
  try:return json.loads(p.read_text())
  except:return {}
 def alive(self,pid):
  try:os.kill(int(pid),0); return True
  except:return False
 def sql(self):
  try:
   c=sqlite3.connect(self.shared/'ticket_locks.sqlite3'); x=c.execute('PRAGMA integrity_check').fetchone()[0]; c.close(); return x
  except Exception as e:return f'error: {e}'
 def _status_attr(self,value):
  v=str(value or '').upper()
  if v in {'ALIVE','HEALTHY','OK','RUNNING','AVAILABLE','LISTENING','ACTIVE'}:return self.c(2)|curses.A_BOLD
  if v in {'READY','STANDBY','SHADOW','APPROVAL','READ-ONLY'}:return self.c(3)|curses.A_BOLD
  if v in {'UNKNOWN','INACTIVE','DISABLED','STOPPED','DEAD','NOT_RUNNING','UNAVAILABLE','FAILED','ERROR'}:return self.c(4)|curses.A_BOLD
  if v in {'GLOBAL','LIMITED'}:return self.c(6)|curses.A_BOLD
  return self.c(1)
 def dashboard(self):
  data={};collector=self.current/'service_status.py'
  if collector.exists():
   try:
    r=subprocess.run([sys.executable,str(collector),'--root',str(self.root),'--json'],text=True,capture_output=True,timeout=15);data=json.loads(r.stdout) if r.returncode==0 else {}
   except Exception:pass
  release=(self.current/'VERSION').read_text().strip() if (self.current/'VERSION').exists() else '?';active=self.read(self.shared/'active_slot.json').get('active_slot','?');self.s.erase();h,w=self.s.getmaxyx();self._safe_add(0,max(1,(w-26)//2),'SOC AUTOMATION CONTROL TUI',curses.A_BOLD|self.c(5));self._safe_add(1,2,'Dashboard',self.c(6));self._safe_add(3,2,f'Release {release} | Active slot: {active}',self.c(7));self._safe_add(5,2,f'{"SERVICE":28} {"MODE":10} {"STATE":10} {"PID":8} HEALTH',curses.A_BOLD|self.c(7));row=6
  for svc in data.get('services',[]):
   name=str(svc.get('name','?'))[:28];mode=str(svc.get('mode') or '-')[:10];state=str(svc.get('state','UNKNOWN'))[:10];pid=str(svc.get('pid') or '-')[:8];health=str(svc.get('health','UNKNOWN'));self._safe_add(row,2,f'{name:28} ',self.c(1));self._safe_add(row,31,f'{mode:10}',self._status_attr(mode));self._safe_add(row,42,f'{state:10}',self._status_attr(state));self._safe_add(row,53,f'{pid:8}',self.c(2)|curses.A_BOLD if pid!='-' else self.c(7));self._safe_add(row,62,health,self._status_attr(health));row+=1
  if not data.get('services'):self._safe_add(row,2,'Service collector unavailable.',self.c(2)|curses.A_BOLD)
  ai={}; ai_tool=self.current/'ai_health.py'
  if ai_tool.is_file():
   try:
    q=subprocess.run([sys.executable,str(ai_tool),'--root',str(self.root)],text=True,capture_output=True,timeout=10)
    ai=json.loads(q.stdout) if q.returncode==0 else {}
   except Exception:ai={}
  if ai and row < h-6:
   row+=1;self._safe_add(row,2,'AI PROVIDER STATUS',curses.A_BOLD|self.c(5));row+=1
   local=ai.get('local_ai') or {};gemini=ai.get('gemini') or {}
   local_mode=str(local.get('mode') or 'UNKNOWN');local_state='AVAILABLE' if local.get('reachable') else 'UNAVAILABLE'
   self._safe_add(row,2,f"{'Local AI':16} model={str(local.get('model') or '-')[:28]:28} mode=",self.c(7));self._safe_add(row,65,local_mode,self._status_attr(local_mode));self._safe_add(row,77,local_state,self._status_attr(local_state));row+=1
   gem_mode=str(gemini.get('mode') or 'UNKNOWN');gem_state=str(gemini.get('status') or 'UNKNOWN')
   self._safe_add(row,2,f"{'Gemini':16} model={str(gemini.get('preferred_model') or '-')[:28]:28} mode=",self.c(7));self._safe_add(row,65,gem_mode,self._status_attr(gem_mode));self._safe_add(row,77,gem_state,self._status_attr(gem_state));row+=1
   self._safe_add(row,2,f"Profile: {ai.get('profile','?')} | Feature revision: {ai.get('revision','?')}",self.c(6))
  self._safe_add(h-2,1,'-'*max(1,w-3),curses.A_DIM);self._safe_add(h-1,2,'Any key: back',self.c(3));self.s.refresh();self.s.getch()
 def ticket_jira_statuses(self, limit=10000):
     events = self.shared / 'control/ticket_events.jsonl'
     statuses = {}
     if not events.is_file():
         return statuses
     try:
         lines = events.read_text(errors='replace').splitlines()[-limit:]
     except OSError:
         return statuses
     for line in lines:
         try:
             event = json.loads(line)
         except (json.JSONDecodeError, TypeError):
             continue
         key = str(event.get('ticket_key') or '')
         details = event.get('details') if isinstance(event.get('details'), dict) else {}
         jira_status = details.get('jira_status')
         if key and jira_status:
             statuses[key] = str(jira_status)
     return statuses
 def live_ticket_processing(self):
     state_file = self.shared / 'control/ticket_live_state.json'
     paused = False
     interval = 1000
     self.s.timeout(interval)
     try:
         while 1:
             h, w = self.frame('Live Ticket Processing', 'Auto-refresh: ' + ('PAUSED' if paused else f'{interval / 1000:g}s') + ' | privacy-safe metadata only')
             try:
                 data = json.loads(state_file.read_text()) if state_file.exists() else {}
             except Exception:
                 data = {}
             now_epoch = dt.datetime.now().astimezone().timestamp()
             rows = sorted([e for e in data.values() if not (str(e.get('status', '')).upper() in {'COMPLETED', 'DISMISSED'} and now_epoch - float(e.get('epoch', 0)) > 30)], key=lambda x: float(x.get('epoch', 0)), reverse=True)
             jira = self.ticket_jira_statuses()
             now = dt.datetime.now().astimezone().timestamp()
             active = {'RUNNING', 'WAITING', 'RETRY', 'BLOCKED'}
             self.s.addnstr(5, 2, f"Tickets tracked: {len(rows)} | Active/recent: {sum((str(x.get('status')) in active for x in rows))}", max(1, w - 4), self.c(1) | curses.A_BOLD)
             if w >= 115:
                 header = f"{'Ticket':<18} {'Worker':<7} {'Stage':<27} {'Pipeline':<11} {'Jira status':<24} Age"
             else:
                 header = f"{'Ticket':<16} {'Worker':<6} {'Stage':<21} {'Jira status':<18} Age"
             self.s.addnstr(7, 2, header, max(1, w - 4), self.c(6) | curses.A_BOLD)
             vis = max(1, h - 11)
             for i, e in enumerate(rows[:vis], 8):
                 age = max(0, int(now - float(e.get('epoch', now))))
                 key = str(e.get('ticket_key', '-'))
                 jira_status = jira.get(key, '-')
                 if w >= 115:
                     line = f"{key:<18.18} {str(e.get('worker', '-')):<7.7} {str(e.get('stage', '-')):<27.27} {str(e.get('status', '-')):<11.11} {jira_status:<24.24} {age:>4}s"
                 else:
                     line = f"{key:<16.16} {str(e.get('worker', '-')):<6.6} {str(e.get('stage', '-')):<21.21} {jira_status:<18.18} {age:>4}s"
                 self.s.addnstr(i, 2, line, max(1, w - 4), self.c(2) if e.get('status') in {'PASS', 'COMPLETED'} else self.c(3))
             self.foot('Auto refresh | Space: pause/resume | +/-: interval | R: refresh | Q/B: back')
             k = self.getkey()
             if k in (ord('q'), ord('Q'), ord('b'), ord('B'), 27):
                 return
             if k == ord(' '):
                 paused = not paused
                 self.s.timeout(-1 if paused else interval)
             elif k in (ord('+'), ord('=')):
                 interval = max(500, interval - 500)
                 self.s.timeout(-1 if paused else interval)
             elif k == ord('-'):
                 interval = min(10000, interval + 500)
                 self.s.timeout(-1 if paused else interval)
     finally:
         self.s.timeout(-1)
 def reconcile_ghost_live_tickets(self):
     tool = self.current / 'live_state_reconciliation_manager.py'
     if not tool.is_file():
         return self.text('Ghost Ticket Reconciliation', 'live_state_reconciliation_manager.py is not installed.')
     ticket = self.ask('Ghost Ticket Reconciliation', 'Ticket key (blank = all stale live tickets):', '')
     if ticket is None:
         return
     prompt = f"Read Jira status and close ghost live-state for {ticket or 'all stale tickets'}? Jira will not be modified."
     if not self.yes('Ghost Ticket Reconciliation', prompt):
         return
     cmd = [sys.executable, str(tool), '--root', str(self.root), '--output', str(self.shared / 'live_state_reconciliation.json')]
     if ticket.strip():
         cmd += ['--ticket', ticket.strip()]
     self.cmd('Ghost Ticket Reconciliation', cmd, timeout=300)
 def ticket_observability(self):
     tool = self.current / 'ticket_observability_report.py'
     if not tool.is_file():
         return self.text('Ticket Observability', 'ticket_observability_report.py is not installed.')
     self.cmd('Ticket Observability', [sys.executable, str(tool), '--root', str(self.root), '--stuck-seconds', '300', '--output', str(self.shared / 'ticket_observability.json')], timeout=120)
 def ticket_history(self):
     tool = self.current / 'ticket_history_manager.py'
     if not tool.is_file():
         return self.text('Ticket History', 'ticket_history_manager.py not installed.')
     result = subprocess.run([sys.executable, str(tool), '--root', str(self.root), 'list'], text=True, capture_output=True, timeout=120)
     try:
         payload = json.loads(result.stdout)
         tickets = payload.get('tickets') if isinstance(payload, dict) else []
     except (json.JSONDecodeError, TypeError):
         return self.text('Ticket History', (result.stdout + '\n' + result.stderr).strip() or 'History unavailable.')
     jira = self.ticket_jira_statuses()
     lines = ['Ticket History | Completed 7d | Failed 30d', '']
     for item in tickets or []:
         key = str(item.get('ticket_key') or '-')
         epoch = item.get('last_epoch')
         stamp = self.format_processing_time(epoch)
         lines.extend(['-' * 72, f'Ticket       : {key}', f"Worker       : {item.get('worker') or '-'}", f"Final stage  : {item.get('stage') or '-'}", f"Pipeline     : {item.get('status') or '-'}", f"Jira status  : {jira.get(key, '-')}", f'Last update  : {stamp}', f"Events       : {item.get('events') or 0}"])
     if not tickets:
         lines.append('No retained ticket history.')
     self.text('Ticket History', '\n'.join(lines))
 def ticket_history_cleanup(self):
     tool = self.current / 'ticket_history_manager.py'
     if self.yes('Ticket History Cleanup', 'Delete completed history older than 7 days and failed history older than 30 days?'):
         self.cmd('Ticket History Cleanup', [sys.executable, str(tool), '--root', str(self.root), 'cleanup', '--completed-days', '7', '--failed-days', '30'], timeout=300)
 def start_all_services(self):
     manual = self.choose('Start ALL - Manual False-Incident', ['DISABLED', 'SHADOW', 'ACTIVE'], 'Select Manual False-Incident mode')
     if manual is None:
         return
     autofp = self.choose('Start ALL - Background Auto-FP', ['DISABLED', 'SHADOW', 'APPROVAL', 'LIMITED', 'GLOBAL'], 'Select Background Auto-FP mode')
     if autofp is None:
         return
     risk = manual == 'ACTIVE' or autofp in ('LIMITED', 'GLOBAL')
     msg = f'Manual={manual} | Auto-FP={autofp}'
     if risk:
         msg += ' | WARNING: selection can modify Jira or SIEM'
     if not self.confirm_choice('Start ALL - Confirm', msg):
         return
     self.cmd('Start All SOC Automation Services', [sys.executable, str(self.current / 'start_all_services.py'), '--root', str(self.root), '--timeout', '120', '--manual-mode', manual, '--autofp-mode', autofp], timeout=210)
 def graceful_stop_all(self):
     if not self.yes('Graceful stop ALL services', 'Disable both action engines, stop both background services, drain and stop the main runtime, verify inactive, and write maintenance audit?'):
         return
     self.cmd('Graceful Stop All SOC Automation Services', [sys.executable, str(self.current / 'graceful_stop_all.py'), '--root', str(self.root), '--timeout', '300'], timeout=390)
 def runtime(self):
  p=sys.executable; ctl=str(self.manager/'socctl.py')
  self.menu('Runtime Control',[('Live ticket processing (auto-refresh)',self.live_ticket_processing),('Reconcile ghost live tickets from Jira',self.reconcile_ghost_live_tickets),('Ticket observability metrics',self.ticket_observability),('Ticket processing history',self.ticket_history),('Cleanup ticket history retention',self.ticket_history_cleanup),('Status',lambda:self.cmd('Status',[p,ctl,'--root',str(self.root),'status'])),('Restart workers',lambda:self.cmd('Restart',[p,ctl,'--root',str(self.root),'restart','--timeout','300'])),('Start ALL SOC Automation services',self.start_all_services),('Graceful stop runtime only',lambda:self.yescmd('Stop runtime only','Stop master and workers after drain? Background services remain running.',[p,ctl,'--root',str(self.root),'stop','--timeout','300'])),('Graceful stop ALL SOC Automation services',self.graceful_stop_all),('Start SocMaster in tmux',self.startmaster)])
 def yescmd(self,title,msg,args):
  if self.yes(title,msg):self.cmd(title,args)
 def startmaster(self):
  if not self.yes('Start Runtime','Start SocMaster in tmux session soc-bot?'):return
  out=self.logs/'soc_master.out'; shell=f'cd {self.manager} && export PYTHONPATH={self.current}:{self.manager} && exec {sys.executable} soc_master.py --root {self.root} >> {out} 2>&1'; self.cmd('Start Runtime',['tmux','new-session','-d','-s','soc-bot',shell])
 def backup(self,reason):
  ts=dt.datetime.now().strftime('%Y%m%d-%H%M%S'); v=(self.current/'VERSION').read_text().strip(); out=self.backups/f'pre-update-{v}-{ts}.tar.gz'
  with tarfile.open(out,'w:gz') as t:
   t.add(self.current,arcname=f'release-{v}',recursive=True)
   for x in ['.env','master.json','active_slot.json','deployment.json','level3_qualification.json']:
    p=self.shared/x
    if p.exists():t.add(p,arcname=f'shared/{x}')
  os.chmod(out,0o600); sha=hashlib.sha256(out.read_bytes()).hexdigest(); s=Path(str(out)+'.sha256'); s.write_text(f'{sha}  {out.name}\n'); os.chmod(s,0o600); self.log('backup_created',details={'reason':reason,'path':str(out),'sha256':sha}); return out
 def maintenance_readiness(self):
  tool=self.current/'maintenance_readiness_report.py'
  if not tool.is_file():return self.text('Maintenance Readiness','maintenance_readiness_report.py is not installed.')
  self.cmd('Maintenance Readiness',[sys.executable,str(tool),'--root',str(self.root),'--output',str(self.shared/'maintenance_readiness.json')],timeout=120)
 def release_qualification(self):
  gate=self.current/'release_qualification_gate.py'
  if not gate.is_file():return self.text('Release Qualification','Gate is not installed in the active release.')
  self.cmd('Release Qualification',[sys.executable,str(gate),'--release',str(self.current),'--report',str(self.shared/'release_qualification.json')],timeout=300)
 def update(self):self.menu('Update Manager',[('Maintenance readiness gate',self.maintenance_readiness),('Apply release patch from path',self.deploy),('Dry-run release patch from path',self.dryrun),('Apply Manager/TUI update from path',self.manager_update),('Create manual backup',self.manualbackup),('Verify latest backup',self.verify_latest_backup),('Run release qualification gate',self.release_qualification),('Deployment status',lambda:self.cmd('Deployment Status',[sys.executable,str(self.manager/'deploy_manager.py'),'--root',str(self.root),'status']))],f'Release {(self.current/"VERSION").read_text().strip()} | TUI {VERSION}')
 def manager_update(self):
  package=self.patchpath()
  if not package.is_file() or package.suffix.lower()!='.zip':return self.text('Invalid Manager Update',str(package))
  try:
   with zipfile.ZipFile(package) as archive:
    if archive.testzip():raise ValueError('ZIP integrity failure')
    names=set(archive.namelist())
    if {'manifest.json','soc_control_tui.py'}-names:raise ValueError('Required manager update files are missing')
    manifest=json.loads(archive.read('manifest.json'))
    if manifest.get('application')!='SOC Automation Manager Update':raise ValueError('Package is not a Manager/TUI update')
    target=str(manifest.get('version') or '')
    minimum_release=str(manifest.get('minimum_release') or '')
    active=(self.current/'VERSION').read_text().strip()
    if minimum_release and tuple(map(int,active.split('.')))<tuple(map(int,minimum_release.split('.'))):raise ValueError(f'Release {active} is older than required {minimum_release}')
    expected=((manifest.get('files') or {}).get('soc_control_tui.py') or {}).get('sha256')
    content=archive.read('soc_control_tui.py'); actual=hashlib.sha256(content).hexdigest()
    if not expected or actual!=expected:raise ValueError('Manager TUI SHA-256 mismatch')
   if not self.yes('Manager/TUI Update',f'Install TUI {target} atomically? The current TUI must be reopened afterward.'):return
   destination=self.manager/'soc_control_tui.py'; backup=self.backups/f'soc_control_tui.py.before-{target}'
   shutil.copy2(destination,backup);os.chmod(backup,0o600)
   with tempfile.TemporaryDirectory(prefix='soc-tui-update-') as td:
    candidate=Path(td)/'soc_control_tui.py';candidate.write_bytes(content);subprocess.run([sys.executable,'-m','py_compile',str(candidate)],check=True,capture_output=True,text=True)
    temporary=destination.with_name('.soc_control_tui.py.new');shutil.copy2(candidate,temporary);os.chmod(temporary,0o700)
    try:
     os.replace(temporary,destination);subprocess.run([sys.executable,'-m','py_compile',str(destination)],check=True,capture_output=True,text=True)
    except Exception:
     if temporary.exists():temporary.unlink()
     shutil.copy2(backup,destination);os.chmod(destination,0o700);raise
   self.log('manager_tui_update','ok',{'version':target,'package':str(package),'backup':str(backup),'sha256':actual})
   self.text('Manager/TUI Update Complete',f'Installed TUI {target}\nBackup: {backup}\nSHA-256: {actual}\n\nExit and reopen the TUI to load the new version.')
  except Exception as e:self.log('manager_tui_update','failed',{'package':str(package),'error':str(e)});self.text('Manager/TUI Update Failed',f'{type(e).__name__}: {e}')
 def patchpath(self):return Path(self.ask('Patch Path','Enter full path to patch ZIP:',str(Path.home()/'storage/downloads'))).expanduser().resolve()
 def dryrun(self):
  p=self.patchpath()
  if not p.is_file():return self.text('Invalid Path',str(p))
  self.cmd('Patch Dry Run',[sys.executable,str(self.manager/'local_release_manager.py'),'--root',str(self.root),'apply','--package',str(p),'--dry-run'])
 def deploy(self):
  p=self.patchpath()
  if not p.is_file() or p.suffix.lower()!='.zip':return self.text('Invalid Patch',str(p))
  if not self.yes('Transactional Update',f'Create backup and deploy {p}?'):return
  try:b=self.backup('pre-update')
  except Exception as e:return self.text('Update Aborted',f'Backup failed: {e}')
  self.log('update_requested',details={'patch':str(p),'backup':str(b)}); ok=self.cmd('Transactional Update',[sys.executable,str(self.manager/'deploy_manager.py'),'--root',str(self.root),'deploy','--package',str(p),'--timeout','300']); self.log('update_completed','ok' if ok else 'failed',{'patch':str(p)})
 def verify_latest_backup(self):
  tool=self.current/'backup_verification_manager.py'
  if not tool.is_file():return self.text('Backup Verification','backup_verification_manager.py is not installed.')
  self.cmd('Verify Latest Backup',[sys.executable,str(tool),'--root',str(self.root),'--output',str(self.shared/'backup_verification.json')],timeout=600)
 def manualbackup(self):
  try:self.text('Backup Complete',str(self.backup('manual')))
  except Exception as e:self.text('Backup Failed',str(e))
 def choosefile(self,title,files,reader):
  if not files:return self.text(title,'No files found')
  p=0
  while 1:
   h,w=self.frame(title,'Read-only'); vis=h-7; start=max(0,min(p-vis//2,len(files)-vis))
   for row,i in enumerate(range(start,min(len(files),start+vis)),4):self.s.addnstr(row,2,files[i].name,w-4,(self.c(5)|curses.A_BOLD) if i==p else 0)
   self.foot('Enter: open | Up/Down | B: back'); k=self.getkey()
   if k in (ord('b'),ord('B'),ord('q'),ord('Q'),27):return
   if k in (curses.KEY_DOWN,ord('j')):p=min(len(files)-1,p+1)
   elif k in (curses.KEY_UP,ord('k')):p=max(0,p-1)
   elif k in (10,13):self.log(f'{title.lower()}_viewed',details={'file':str(files[p])}); self.text(files[p].name,reader(files[p]))
 def audits(self):
  fs=sorted((self.shared/'audit_logs').glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)
  self.choosefile('Audit Viewer',fs,lambda p:json.dumps(json.loads(p.read_text()),indent=2,ensure_ascii=False))
 def logview(self):
  fs=sorted([p for p in self.logs.glob('*') if p.is_file()],key=lambda p:p.stat().st_mtime,reverse=True)
  self.choosefile('Log Viewer',fs,lambda p:'\n'.join(p.read_text(errors='replace').splitlines()[-500:]))
 def system_health(self):
  syn=subprocess.run([sys.executable,'-m','py_compile',str(self.current/'main.py'),str(self.current/'privacy_manager.py'),str(self.current/'soc_status.py')],capture_output=True,text=True); free=shutil.disk_usage(self.root).free//1048576; self.log('diagnostics_system_health','ok' if syn.returncode==0 else 'failed'); self.text('System Health',f'Version: {(self.current/"VERSION").read_text().strip()}\nCurrent: {self.current.resolve()}\nSQLite: {self.sql()}\nFree space: {free} MiB\nPython: {sys.version.split()[0]}\ntmux: {shutil.which("tmux") or "missing"}\nSyntax: {"PASS" if syn.returncode==0 else "FAIL"}\n{syn.stderr}')
 def local_ai_health(self):
  code="""import json,time
from config import settings
import requests
from local_ai_detector import OllamaSensitiveDetector
cfg=settings.local_ai
endpoint=str(cfg.endpoint).rstrip('/')
result={'provider':cfg.provider,'endpoint':endpoint,'endpoint_local':endpoint.startswith(('http://127.0.0.1:','http://localhost:')),'configured_model':cfg.model,'service_reachable':False,'model_available':False,'schema_probe':False,'response_ms':None,'error':None}
started=time.monotonic()
try:
 response=requests.get(endpoint+'/api/tags',timeout=min(10,cfg.request_timeout));response.raise_for_status();result['service_reachable']=True
 models=[str(item.get('name') or item.get('model') or '') for item in response.json().get('models',[])]
 configured=str(cfg.model or '');result['model_available']=configured in models or any(name.split(':')[0]==configured.split(':')[0] for name in models)
 if result['model_available']:
  detector=OllamaSensitiveDetector(cfg);findings=detector.detect({'host':{'name':'diagnostic-host'}});result['schema_probe']=isinstance(findings,list)
except Exception as exc:result['error']=f'{type(exc).__name__}: {exc}'
result['response_ms']=round((time.monotonic()-started)*1000,1)
result['status']='PASS' if all((result['endpoint_local'],result['service_reachable'],result['model_available'],result['schema_probe'])) else 'FAIL'
print(json.dumps(result,indent=2))"""
  r=subprocess.run([sys.executable,'-c',code],cwd=self.current,text=True,capture_output=True,timeout=120); status='ok' if r.returncode==0 and '"status": "PASS"' in r.stdout else 'failed';self.log('diagnostics_local_ai',status,{'returncode':r.returncode});self.text('Local AI Health',(r.stdout+'\n'+r.stderr).strip() or '(no output)')
 def privacy_regression(self):
  tests=[self.current/'tests/test_path_scoped_sanitizer.py',self.current/'tests/test_privacy_manager.py',self.current/'tests/test_offset_propagation_hardening.py']; output=[]; passed=0
  for test in tests:
   if not test.is_file():output.append(f'FAIL {test.name}: file not found');continue
   r=subprocess.run([sys.executable,str(test)],cwd=self.current,text=True,capture_output=True,timeout=180); ok=r.returncode==0; passed+=int(ok); output.append(f'{"PASS" if ok else "FAIL"} {test.name} (rc={r.returncode})'); output.extend('  '+line for line in (r.stdout+'\n'+r.stderr).strip().splitlines()[-12:])
  status='PASS' if passed==len(tests) else 'FAIL'; self.log('diagnostics_privacy_regression','ok' if status=='PASS' else 'failed',{'passed':passed,'failed':len(tests)-passed}); self.text('Privacy Regression Tests','\n'.join(output+['',f'Passed: {passed}',f'Failed: {len(tests)-passed}',f'Status: {status}']))
 def server01_diagnostic(self):
  code="import json,os,tempfile;os.environ['AUDIT_DIR']=tempfile.mkdtemp(prefix='soc-server01-tui-');from privacy_manager import PrivacyManager;payload={'host':{'name':'server01'},'kibana.alert.reason':'event on server01'};m=PrivacyManager();m.local_ai_detector=type('EmptyLocalAIDetector',(),{'detect':lambda self,payload:[]})();r=m.prepare_payload(ticket_key='SERVER01-TUI-DIAGNOSTIC',raw_json=json.dumps(payload));s=json.loads(r.sanitized_json);h=s['host']['name'];q=s['kibana.alert.reason'];c={'raw_server01_remaining':r.sanitized_json.count('server01'),'pseudonyms_consistent':q=='event on '+h,'host_is_pseudonym':h.startswith('HOST_'),'safe_for_ai':r.safe_for_ai,'residual_count':r.residual_count};e={'raw_server01_remaining':0,'pseudonyms_consistent':True,'host_is_pseudonym':True,'safe_for_ai':True,'residual_count':0};print(json.dumps({'sanitized':s,'checks':c,'status':'PASS' if c==e else 'FAIL'},indent=2))"
  r=subprocess.run([sys.executable,'-c',code],cwd=self.current,text=True,capture_output=True,timeout=120); self.log('diagnostics_server01','ok' if r.returncode==0 and '"status": "PASS"' in r.stdout else 'failed',{'returncode':r.returncode}); self.text('Server01 Sanitizer Diagnostic',(r.stdout+'\n'+r.stderr).strip() or '(no output)')
 def runtime_health_center(self):
  tool=self.current/'runtime_health_report.py'
  if not tool.is_file():return self.text('Runtime Health Center','runtime_health_report.py is not installed.')
  self.cmd('Runtime Health Center',[sys.executable,str(tool),'--root',str(self.root),'--output',str(self.shared/'runtime_health_center.json')],timeout=120)
 def operational_alert_history(self):
  path=self.shared/'control/operational_alerts.jsonl'
  if not path.is_file():return self.text('Operational Alerts','No operational alerts recorded.')
  lines=[]
  for raw in path.read_text(errors='replace').splitlines()[-100:]:
   try:e=json.loads(raw)
   except Exception:continue
   d=e.get('details') if isinstance(e.get('details'),dict) else {};lines.append(f"{self.format_processing_time(e.get('epoch'))} | {e.get('severity','-')} | {e.get('component','-')} | {e.get('code','-')} | worker={d.get('worker','-')} | telegram={'sent' if e.get('telegram_sent') else 'not-sent'} | deduped={e.get('deduped',False)}")
  self.text('Operational Alerts','\n'.join(lines) or 'No operational alerts recorded.')
 def vt_status(self):self.cmd('VirusTotal Status',[sys.executable,str(self.current/'virustotal_manager.py'),'--root',str(self.root),'status'],timeout=60)
 def vt_set_key(self):
  key=self.ask_secret('VirusTotal API Key','API key (input hidden):')
  if key:
   p=subprocess.run([sys.executable,str(self.current/'virustotal_manager.py'),'--root',str(self.root),'set-key','--stdin'],input=key+'\n',text=True,capture_output=True,timeout=60);self.text('VirusTotal API Key',p.stdout or p.stderr)
 def vt_lookup(self):
  ip=self.ask('VirusTotal IP Lookup','Public IP','').strip()
  if ip:self.cmd('VirusTotal IP Lookup',[sys.executable,str(self.current/'virustotal_manager.py'),'--root',str(self.root),'lookup',ip,'--force'],timeout=60)
 def vt_clear(self):
  if self.yes('VirusTotal Cache','Clear local VirusTotal IP cache?'):self.cmd('VirusTotal Cache',[sys.executable,str(self.current/'virustotal_manager.py'),'--root',str(self.root),'clear-cache'],timeout=60)
 def virustotal_menu(self):self.menu('VirusTotal Integration',[('Show configuration status',self.vt_status),('Configure API key (hidden input)',self.vt_set_key),('Test public IP reputation',self.vt_lookup),('Clear reputation cache',self.vt_clear)],'Enrichment only | no auto-FP | public IP only')
 def smb_correlation_test(self):
  alert=self.ask('SMB Correlation','Alert JSON path','').strip();events=self.ask('SMB Correlation','Related events JSON path','').strip()
  if alert and events:self.cmd('SMB Correlation',[sys.executable,str(self.current/'smb_correlation_manager.py'),'--alert',alert,'--events',events],timeout=60)
 def smb_correlation_menu(self):self.menu('External SMB Correlation',[('Assess exported alert and related events',self.smb_correlation_test)],'Analyst assist only | no auto-FP')
 def smb_risk_test(self):
  alert=self.ask('SMB Risk Correlation','Alert JSON path','').strip();events=self.ask('SMB Risk Correlation','Related events JSON path','').strip();alerts=self.ask('SMB Risk Correlation','Related alerts JSON path','').strip();vt=self.ask('SMB Risk Correlation','VirusTotal result JSON path (optional)','').strip()
  if alert and events and alerts:
   cmd=[sys.executable,str(self.current/'smb_risk_manager.py'),'--alert',alert,'--events',events,'--alerts',alerts]
   if vt:cmd += ['--vt',vt]
   self.cmd('SMB Related Risk Correlation',cmd,timeout=60)
 def smb_risk_menu(self):self.menu('SMB Related Risk Correlation',[('Assess exported evidence (dry-run)',self.smb_risk_test)],'Recommendation only | no Jira change | no auto-FP')
 def smb_auto_dry_run(self):
  ticket=self.ask('Automated SMB Dry-Run','Ticket key from audit log (example: CSOC-103398)','').strip().upper()
  if ticket:self.cmd('Automated SMB Evidence Collection',[sys.executable,str(self.current/'smb_auto_dry_run.py'),'--root',str(self.root),'--ticket',ticket],timeout=120)
 def smb_auto_menu(self):self.menu('Automated SMB Evidence Collection',[('Collect evidence and assess (dry-run)',self.smb_auto_dry_run)],'Audit log + scoped fan-out + cluster VT | dry-run only')
 def autofp_status(self):self.cmd('Controlled Auto-FP Status',[sys.executable,str(self.current/'controlled_autofp_manager.py'),'--root',str(self.root),'status'],timeout=60)
 def autofp_enable(self):
  ack=self.ask('Enable Controlled Auto-FP','Type ENABLE-CONTROLLED-AUTO-FP','').strip()
  if ack:self.cmd('Enable Controlled Auto-FP',[sys.executable,str(self.current/'controlled_autofp_manager.py'),'--root',str(self.root),'enable','--ack',ack],timeout=60)
 def autofp_disable(self):self.cmd('Disable Controlled Auto-FP',[sys.executable,str(self.current/'controlled_autofp_manager.py'),'--root',str(self.root),'disable'],timeout=60)
 def autofp_test(self):
  ticket=self.ask('Controlled Auto-FP','Ticket key','').strip().upper()
  if ticket:self.cmd('Controlled Auto-FP Gate Test',[sys.executable,str(self.current/'controlled_autofp_manager.py'),'--root',str(self.root),'run',ticket],timeout=60)
 def autofp_apply(self):
  ticket=self.ask('Controlled Auto-FP APPLY','Eligible ticket key','').strip().upper()
  if ticket and self.yes('Controlled Auto-FP APPLY','Transition Jira to False Incident then Done?'):self.cmd('Controlled Auto-FP APPLY',[sys.executable,str(self.current/'controlled_autofp_manager.py'),'--root',str(self.root),'run',ticket,'--apply'],timeout=120)
 def autofp_menu(self):self.menu('Controlled Auto-FP Pilot',[('Show pilot status',self.autofp_status),('Test gate only',self.autofp_test),('Enable pilot with acknowledgement',self.autofp_enable),('Disable pilot kill switch',self.autofp_disable),('Apply eligible ticket',self.autofp_apply)],'Default disabled | CSOC only | caps 2/hour 5/day | Jira only')
 def bgfp_status(self):self.cmd('Background Auto-FP Status',[sys.executable,str(self.current/'background_autofp_worker.py'),'--root',str(self.root),'status'],timeout=60)
 def bgfp_mode(self):
  value=self.choose('Background Auto-FP Mode',['DISABLED','SHADOW','APPROVAL','LIMITED','GLOBAL'],'Select operating mode')
  if value is None:return
  if value in ('DISABLED','SHADOW','APPROVAL','LIMITED','GLOBAL'):
   if value in ('LIMITED','GLOBAL') and not self.yes('High-impact mode',f'Enable {value} unattended Jira actions?'):return
   self.cmd('Set Background Auto-FP Mode',[sys.executable,str(self.current/'background_autofp_worker.py'),'--root',str(self.root),'mode',value],timeout=60)
 def bgfp_ticket(self):
  ticket=self.ask('Background Auto-FP','Ticket key','').strip().upper()
  if ticket:self.cmd('Background Auto-FP Ticket',[sys.executable,str(self.current/'background_autofp_worker.py'),'--root',str(self.root),'run-ticket',ticket],timeout=120)
 def bgfp_menu(self):self.menu('Background Auto-FP Foundation',[('Show background state',self.bgfp_status),('Set operating mode',self.bgfp_mode),('Process one ticket through background path',self.bgfp_ticket)],'Default SHADOW | per-ticket binding | 15-minute TTL | idempotent')
 def afsvc(self,cmd):self.cmd('Auto-FP Service '+cmd,[sys.executable,str(self.current/'autofp_service_manager.py'),'--root',str(self.root),cmd],timeout=90)
 def afsvc_install(self):self.afsvc('install')
 def afsvc_start(self):self.afsvc('start')
 def afsvc_stop(self):self.afsvc('stop')
 def afsvc_restart(self):self.afsvc('restart')
 def afsvc_status(self):self.afsvc('status')
 def afsvc_poll(self):self.cmd('Auto-FP Poll Once',[sys.executable,str(self.current/'autofp_service_cli.py'),'--root',str(self.root),'poll-once'],timeout=180)
 def afsvc_circuit(self):
  if self.yes('Reset circuit breaker','Reset only after root cause is resolved?'):self.cmd('Reset Auto-FP Circuit',[sys.executable,str(self.current/'autofp_service_cli.py'),'--root',str(self.root),'reset-circuit'],timeout=60)
 def afsvc_menu(self):self.menu('Background Auto-FP Service',[('Install/update user service',self.afsvc_install),('Show service status',self.afsvc_status),('Poll once now',self.afsvc_poll),('Start service',self.afsvc_start),('Stop service',self.afsvc_stop),('Restart service',self.afsvc_restart),('Reset circuit breaker',self.afsvc_circuit)],'Default SHADOW | polls every 60s | circuit breaker fail-closed')
 def mfi_cmd(self,title,args,timeout=90):self.cmd(title,[sys.executable,str(self.current/args[0]),'--root',str(self.root),*args[1:]],timeout=timeout)
 def mfi_status(self):self.mfi_cmd('Manual False-Incident Status',['manual_false_incident_cli.py','status'])
 def mfi_poll(self):self.mfi_cmd('Manual False-Incident Poll Once',['manual_false_incident_cli.py','poll-once'],180)
 def mfi_mode(self):
  value=self.choose('Manual False-Incident Mode',['DISABLED','SHADOW','ACTIVE'],'Select operating mode')
  if value is None:return
  if value=='ACTIVE' and not self.yes('Enable ACTIVE reconciliation','False Incident assigned to your Jira account will move to Done and close the bound SIEM alert. Continue?'):return
  if value in ('DISABLED','SHADOW','ACTIVE'):self.mfi_cmd('Set Manual False-Incident Mode',['manual_false_incident_cli.py','mode',value])
 def mfi_service(self,cmd):self.mfi_cmd('Manual False-Incident Service '+cmd,['manual_false_incident_service.py',cmd])
 def mfi_menu(self):self.menu('Manual False-Incident Reconciliation',[('Show status',self.mfi_status),('Poll once now',self.mfi_poll),('Set mode',self.mfi_mode),('Install/update service',lambda:self.mfi_service('install')),('Show service status',lambda:self.mfi_service('status')),('Start service',lambda:self.mfi_service('start')),('Stop service',lambda:self.mfi_service('stop')),('Restart service',lambda:self.mfi_service('restart'))],'Default SHADOW | assignee account ID required | Jira Done then SIEM False Positive')
 def configuration_preflight(self):
  tool=self.current/'configuration_preflight_report.py'
  if not tool.is_file():return self.text('Configuration Preflight','configuration_preflight_report.py is not installed.')
  self.cmd('Configuration Preflight',[sys.executable,str(tool),'--root',str(self.root),'--output',str(self.shared/'configuration_preflight.json')],timeout=120)
 def diagnostics(self):self.menu('Diagnostics',[('Runtime health center',self.runtime_health_center),('Operational alert history',self.operational_alert_history),('VirusTotal integration',self.virustotal_menu),('External SMB correlation',self.smb_correlation_menu),('SMB related risk correlation',self.smb_risk_menu),('Automated SMB evidence collection',self.smb_auto_menu),('Controlled Auto-FP pilot',self.autofp_menu),('Background Auto-FP foundation',self.bgfp_menu),('Background Auto-FP service',self.afsvc_menu),('Manual False-Incident reconciliation',self.mfi_menu),('Configuration preflight and effective sources',self.configuration_preflight),('System health',self.system_health),('Local AI health',self.local_ai_health),('Privacy regression tests',self.privacy_regression),('Server01 sanitizer diagnostic',self.server01_diagnostic)],'Local-only diagnostics; Local AI probe uses dummy data')
 def viewer(self):self.menu('Viewer Services',[('Status Viewer',self.status_viewer_menu),('Documentation Viewer',self.documentation_viewer_menu)],'Localhost-only read-only web services')
 def status_viewer_menu(self):self.menu('Status Viewer',[('Start status viewer',self.startviewer),('Stop status viewer',lambda:self.cmd('Stop Status Viewer',['tmux','kill-session','-t','soc-viewer'])),('Status viewer status',self.viewerstatus),('Status viewer URL',lambda:self.text('Status Viewer URL','http://127.0.0.1:8765\nRead-only interface'))])
 def documentation_viewer_menu(self):
  if not (self.current/'soc_docs_server.py').is_file():return self.text('Documentation Viewer','soc_docs_server.py is not installed. Release 5.4.12 or newer is required.')
  self.menu('Documentation Viewer',[('Start documentation viewer',self.startdocs),('Stop documentation viewer',lambda:self.cmd('Stop Documentation Viewer',['tmux','kill-session','-t','soc-docs'])),('Documentation viewer status',self.docsstatus),('Documentation viewer URL',lambda:self.text('Documentation Viewer URL','http://127.0.0.1:8766\nRead-only local documentation')),('Build / refresh documentation',self.builddocs)])
 def startdocs(self):
  out=self.logs/'soc_docs.out';shell=f'cd {self.current} && export PYTHONPATH={self.current} && exec {sys.executable} soc_docs_server.py --root {self.root} --host 127.0.0.1 --port 8766 >> {out} 2>&1';self.cmd('Start Documentation Viewer',['tmux','new-session','-d','-s','soc-docs',shell])
 def docsstatus(self):
  r=subprocess.run(['tmux','has-session','-t','soc-docs'],capture_output=True);self.text('Documentation Viewer Status','RUNNING: http://127.0.0.1:8766' if r.returncode==0 else 'STOPPED')
 def builddocs(self):self.cmd('Build Documentation',[sys.executable,str(self.current/'soc_docs_server.py'),'--root',str(self.root),'--host','127.0.0.1','--port','8766','--build-only'],timeout=120)
 def startviewer(self):
  out=self.logs/'soc_viewer.out'; shell=f'cd {self.current} && export PYTHONPATH={self.current} && exec {sys.executable} soc_viewer.py --root {self.root} --host 127.0.0.1 --port 8765 >> {out} 2>&1'; self.cmd('Start Viewer',['tmux','new-session','-d','-s','soc-viewer',shell])
 def viewerstatus(self):
  r=subprocess.run(['tmux','has-session','-t','soc-viewer'],capture_output=True); self.text('Viewer Status','RUNNING: http://127.0.0.1:8765' if r.returncode==0 else 'STOPPED')
 def releases(self):
  def ls():self.text('Installed Releases','\n'.join(p.name for p in sorted((self.root/'releases').glob('v*'),reverse=True)))
  def rb():
   if self.yes('Rollback','Rollback previous release and restart workers?') and self.cmd('Rollback',[sys.executable,str(self.manager/'local_release_manager.py'),'--root',str(self.root),'rollback']):self.cmd('Restart',[sys.executable,str(self.manager/'socctl.py'),'--root',str(self.root),'restart','--timeout','300'])
  self.menu('Release and Rollback',[('List releases',ls),('Rollback previous release',rb),('Release metadata',lambda:self.text('Release Metadata',(self.current/'RELEASE.json').read_text() if (self.current/'RELEASE.json').exists() else 'No metadata'))])
 def secret_scan_menu(self):
  self.menu('Secret Scan and Distribution',[
   ('Scan active release and manager',self.scan_active),
   ('Scan installer ZIP',self.scan_zip),
   ('Build safe full installer',self.build_safe_installer),
   ('Show latest scan report',self.show_scan_report),
  ],'Fail-closed: installer is published only when every scan passes')
 def builder_path(self):
  self.ensure_portability_fix()
  path=self.manager/'build_full_local_installer.py'
  text=path.read_text(encoding='utf-8',errors='replace') if path.is_file() else ''
  required=('installer-generation-v1.27.11','--scan-only','active_allowlisted_source_scan','accepted_test_fixtures')
  if not all(marker in text for marker in required):raise RuntimeError('Builder v1.27.10 self-healing validation failed')
  return path
 def report_path(self):
  return self.shared/'installer_scan_report.json'
 def scan_active(self):
  builder=self.builder_path()
  if not builder.exists():return self.text('Secret Scan','Builder not installed: '+str(builder))
  out=self.shared/'distribution-scan-temp';out.mkdir(parents=True,exist_ok=True)
  args=[sys.executable,str(builder),'--root',str(self.root),'--output',str(out),'--scan-only','--report',str(self.report_path())]
  self.cmd('Scan Active Release',args,timeout=900)
 def scan_zip(self):
  raw=self.ask('Installer ZIP Scan','Enter full path to installer ZIP:',str(Path.home()/'storage/downloads'))
  package=Path(raw).expanduser().resolve()
  if not package.is_file():return self.text('Invalid Package',str(package))
  builder=self.builder_path()
  if not builder.exists():return self.text('Secret Scan','Builder not installed: '+str(builder))
  self.cmd('Scan Installer ZIP',[sys.executable,str(builder),'--scan-package',str(package),'--report',str(self.report_path())],timeout=900)
 def build_safe_installer(self):
  output=Path(self.ask('Safe Installer Build','Output directory:',str(Path.home()/'storage/downloads'))).expanduser().resolve()
  builder=self.builder_path()
  if not builder.exists():return self.text('Build Blocked','Builder not installed: '+str(builder))
  if not self.yes('Safe Installer Build',f'Run source scan, staging scan, build, extract-and-rescan, manifest verification, and SHA-256 generation? Output: {output}'):return
  output.mkdir(parents=True,exist_ok=True)
  args=[sys.executable,str(builder),'--root',str(self.root),'--output',str(output),'--report',str(self.report_path())]
  ok=self.cmd('Safe Full Installer Build',args,timeout=1800)
  self.log('safe_installer_build','ok' if ok else 'failed',{'output':str(output),'report':str(self.report_path())})
 def show_scan_report(self):
  report=self.report_path()
  if not report.exists():return self.text('Secret Scan Report','No report is available yet.')
  try:data=json.loads(report.read_text(encoding='utf-8'));content=json.dumps(data,indent=2,ensure_ascii=False)
  except Exception:content=report.read_text(encoding='utf-8',errors='replace')
  self.text('Latest Secret Scan Report',content)
 def processing_state_rows(self):
  database=self.shared/'ticket_locks.sqlite3'
  if not database.is_file():return []
  connection=sqlite3.connect(database,timeout=10)
  try:
   connection.row_factory=sqlite3.Row
   rows=connection.execute(
    '''
    SELECT
     ticket_key,
     state,
     attempts,
     COALESCE(failure_code,'') AS failure_code,
     next_retry_at,
     cooldown_until,
     completed_at,
     updated_at
    FROM ticket_processing_state
    ORDER BY
     CASE state
      WHEN 'blocked_manual_review' THEN 1
      WHEN 'retry_wait' THEN 2
      WHEN 'processing' THEN 3
      WHEN 'completed' THEN 4
      ELSE 5
     END,
     updated_at DESC,
     ticket_key
    '''
   ).fetchall()
   return [dict(row) for row in rows]
  finally:
   connection.close()
 def format_processing_time(self,value):
  if value is None:return '-'
  try:
   return dt.datetime.fromtimestamp(
    float(value),
    tz=dt.datetime.now().astimezone().tzinfo,
   ).isoformat(timespec='seconds')
  except (TypeError,ValueError,OSError):
   return 'invalid'
 def retry_queue_status(self):
  rows=self.processing_state_rows()
  selected=[
   row for row in rows
   if row.get('state') in {
    'retry_wait',
    'processing',
    'blocked_manual_review',
   }
  ]
  if not selected:
   return self.text(
    'Retry Queue and Manual Review',
    'Tidak ada tiket retry, processing, atau manual review.',
   )
  output=[]
  counts={}
  for row in selected:
   state=str(row.get('state') or 'unknown')
   counts[state]=counts.get(state,0)+1
  output.append('STATE SUMMARY')
  for state,count in sorted(counts.items()):
   output.append(f'{state}: {count}')
  output.append('')
  output.append('TICKET DETAILS')
  for row in selected:
   output.extend([
    '-'*72,
    f"Ticket       : {row.get('ticket_key','-')}",
    f"State        : {row.get('state','-')}",
    f"Attempts     : {row.get('attempts',0)}",
    f"Failure code : {row.get('failure_code') or '-'}",
    (
     'Next retry   : '
     +self.format_processing_time(
      row.get('next_retry_at')
     )
    ),
    (
     'Cooldown     : '
     +self.format_processing_time(
      row.get('cooldown_until')
     )
    ),
    (
     'Updated      : '
     +self.format_processing_time(
      row.get('updated_at')
     )
    ),
   ])
  self.log(
   'retry_queue_viewed',
   details={
    'rows':len(selected),
    'counts':counts,
   },
  )
  self.text(
   'Retry Queue and Manual Review',
   '\n'.join(output),
  )
 def select_reprocess_tickets(self):
  rows=[row for row in self.processing_state_rows() if row.get('state') in {'blocked_manual_review','retry_wait'}]
  def ticket_sort_key(row):
   key=str(row.get('ticket_key') or '').upper()
   match=re.fullmatch(r'([A-Z][A-Z0-9_]*)-(\d+)',key)
   return (match.group(1),int(match.group(2))) if match else (key,-1)
  rows.sort(key=ticket_sort_key)
  if not rows:
   self.text('Select Blocked Tickets','Tidak ada tiket blocked_manual_review atau retry_wait.')
   return []
  p=0;selected=set()
  while 1:
   h,w=self.frame('Select Blocked Tickets',f'{len(rows)} available | {len(selected)} selected')
   vis=max(1,h-7);start=max(0,min(p-vis//2,len(rows)-vis))
   for screen_row,index in enumerate(range(start,min(len(rows),start+vis)),4):
    row=rows[index];key=str(row.get('ticket_key') or '');mark='[x]' if key in selected else '[ ]';cursor='▶' if index==p else ' '
    label=f"{cursor} {mark} {key:<16} {row.get('state','-'):<23} attempts={row.get('attempts',0):<3} {row.get('failure_code') or '-'}"
    self.s.addnstr(screen_row,2,label,max(1,w-4),(self.c(5)|curses.A_BOLD) if index==p else self.c(1))
   self.foot('Space: toggle | A: all/none | Enter: continue | Up/Down | B/Q: back');k=self.getkey()
   if k in (ord('b'),ord('B'),ord('q'),ord('Q'),27):return []
   if k in (curses.KEY_DOWN,ord('j')):p=min(len(rows)-1,p+1)
   elif k in (curses.KEY_UP,ord('k')):p=max(0,p-1)
   elif k==ord(' '):
    key=str(rows[p].get('ticket_key') or '')
    if key in selected:selected.remove(key)
    else:selected.add(key)
   elif k in (ord('a'),ord('A')):
    selected=set() if len(selected)==len(rows) else {str(row.get('ticket_key') or '') for row in rows}
   elif k in (10,13,curses.KEY_ENTER):
    if selected:return [str(row.get('ticket_key') or '') for row in rows if str(row.get('ticket_key') or '') in selected]
 def select_reprocess_ticket(self):
  selected=self.select_reprocess_tickets()
  return selected[0] if selected else None
 def ticket_reprocess_key(self):
  return self.select_reprocess_ticket()
 def run_ticket_batch(self,title,command,keys,timeout):
  lines=[];passed=0
  for index,key in enumerate(keys,1):
   self.frame(title,f'{index}/{len(keys)} {key}');self.s.refresh()
   result=subprocess.run([sys.executable,str(self.current/'ticket_reprocess.py'),'--root',str(self.root),command,key],text=True,capture_output=True,timeout=timeout)
   semantic_status=None
   try:
    payload=json.loads(result.stdout)
    if command=='retest':semantic_status=str(payload.get('status') or '').upper()
    elif command=='requeue':semantic_status=str(payload.get('status') or '').upper()
    elif command=='state':semantic_status='PASS' if payload.get('state') is not None else 'FAIL'
   except (json.JSONDecodeError,TypeError,AttributeError):
    semantic_status=None
   if command=='retest':ok=result.returncode==0 and semantic_status=='PASS'
   elif command=='requeue':ok=result.returncode==0 and semantic_status=='REQUEUED'
   else:ok=result.returncode==0 and semantic_status=='PASS'
   passed+=int(ok);lines.append(f'{"PASS" if ok else "FAIL"} {key} (rc={result.returncode}, status={semantic_status or "UNREADABLE"})');lines.extend('  '+line for line in (result.stdout+'\n'+result.stderr).strip().splitlines())
  failed=len(keys)-passed
  self.log('ticket_reprocess_batch','ok' if failed==0 else 'partial',{'command':command,'selected':len(keys),'passed':passed,'failed':failed})
  self.text(title,'\n'.join(lines+['',f'Selected: {len(keys)}',f'Passed: {passed}',f'Failed: {failed}',f'Status: {"PASS" if failed==0 else "PARTIAL"}']))
 def ticket_state(self):
  keys=self.select_reprocess_tickets()
  if keys:self.run_ticket_batch('Ticket Processing State','state',keys,60)
 def ticket_privacy_retest(self):
  keys=self.select_reprocess_tickets()
  if keys:self.run_ticket_batch('Ticket Privacy Re-test','retest',keys,180)
 def ticket_requeue(self):
  keys=self.select_reprocess_tickets()
  if not keys:return
  preview=', '.join(keys[:5])+(' ...' if len(keys)>5 else '')
  if not self.yes('Validated Ticket Requeue',f'Re-test and requeue {len(keys)} selected ticket(s) only when each privacy gate passes? {preview}'):return
  self.run_ticket_batch('Validated Ticket Requeue','requeue',keys,180)
 def ticket_dismiss(self):
  keys=self.select_reprocess_tickets()
  if not keys:return
  reason=self.choose('Dismiss Reprocessing Reason',['jira_done_manual','false_positive_manual','duplicate_ticket','no_further_analysis','other'],'Select dismissal reason')
  if reason is None:return
  allowed={'jira_done_manual','false_positive_manual','duplicate_ticket','no_further_analysis','other'}
  if reason not in allowed:return self.text('Dismiss Reprocessing','Invalid reason.')
  preview=', '.join(keys[:5])+(' ...' if len(keys)>5 else '')
  if not self.yes('Dismiss Reprocessing',f'Dismiss {len(keys)} ticket(s) and schedule raw cleanup after 7 days? {preview}'):return
  tool=self.current/'ticket_reprocess.py';lines=[];passed=0
  for key in keys:
   r=subprocess.run([sys.executable,str(tool),'--root',str(self.root),'dismiss',key,'--reason',reason,'--cleanup-grace-days','7'],text=True,capture_output=True,timeout=60);ok=r.returncode==0 and '"status": "DISMISSED"' in r.stdout;passed+=int(ok);lines.append(f'{"PASS" if ok else "FAIL"} {key}');lines.extend('  '+x for x in (r.stdout+r.stderr).strip().splitlines())
  self.log('ticket_dismiss','ok' if passed==len(keys) else 'partial',{'selected':len(keys),'passed':passed,'reason':reason});self.text('Dismiss Reprocessing','\n'.join(lines))
 def ticket_restore(self):
  key=self.ask('Restore Reprocessing','Enter dismissed ticket key:','').strip().upper()
  if not re.fullmatch(r'[A-Z][A-Z0-9_]+-[0-9]+',key):return self.text('Restore Reprocessing','Invalid ticket key.')
  if not self.yes('Restore Reprocessing',f'Restore dismissed ticket {key}? Raw audit must still exist.'):return
  tool=self.current/'ticket_reprocess.py';r=subprocess.run([sys.executable,str(tool),'--root',str(self.root),'restore',key],text=True,capture_output=True,timeout=60);ok=r.returncode==0 and '"status": "RESTORED"' in r.stdout;self.log('ticket_restore','ok' if ok else 'failed',{'ticket':key});self.text('Restore Reprocessing',(r.stdout+'\n'+r.stderr).strip())
 def audit_retention_preview(self):
  tool=self.current/'audit_retention_manager.py';self.cmd('Audit Retention Preview',[sys.executable,str(tool),'--root',str(self.root),'--raw-days','14','--sanitized-days','90'],timeout=300)
 def audit_retention_apply(self):
  tool=self.current/'audit_retention_manager.py'
  if self.yes('Audit Retention','Delete eligible audit files? Retryable, processing, and unknown states remain protected.'):self.cmd('Audit Retention Apply',[sys.executable,str(tool),'--root',str(self.root),'--raw-days','14','--sanitized-days','90','--apply'],timeout=300)
 def ticket_reprocessing_menu(self):
  tool=self.current/'ticket_reprocess.py'
  if not tool.is_file():return self.text('Ticket Reprocessing','ticket_reprocess.py is not installed. Release 5.4.8 or newer is required.')
  self.menu('Ticket Reprocessing',[('Show ticket processing state',self.ticket_state),('Privacy re-test saved raw audit',self.ticket_privacy_retest),('Requeue validated ticket',self.ticket_requeue),('Dismiss reprocessing (7-day raw grace)',self.ticket_dismiss),('Restore dismissed ticket',self.ticket_restore),('Audit retention preview',self.audit_retention_preview),('Apply audit retention',self.audit_retention_apply)],'Dismiss creates a tombstone; retryable, processing, and unknown states remain protected')
 def sharing_allowlist_list(self):
  self.cmd('Approved Sharing Allowlist',[sys.executable,str(self.current/'sharing_allowlist_manager.py'),'--root',str(self.root),'list'],timeout=60)
 def sharing_allowlist_add(self):
  kind=self.choose('Allowlist Add Type',['DOMAIN','EMAIL'],'Select allowlist entry type')
  if kind is None:
   return
  label='Domain' if kind=='DOMAIN' else 'Email address'
  value=self.ask('Allowlist Add',label,'').strip()
  if not value:
   self.text('Allowlist Add','Cancelled: value is required.')
   return
  classification=self.choose('Allowlist Classification',['VENDOR','INTERNAL'],'Select classification')
  if classification is None:
   return
  reason=self.ask('Allowlist Add','Business reason','Approved collaboration target').strip()
  if not reason:
   self.text('Allowlist Add','Cancelled: business reason is required.')
   return
  reference=self.ask('Allowlist Add','Approval/change reference','CHG-').strip()
  if not reference:
   self.text('Allowlist Add','Cancelled: approval/change reference is required.')
   return
  expiry=self.ask('Allowlist Add','Expiry YYYY-MM-DD (blank = none)','').strip()
  summary='Type: %s\nValue: %s\nClassification: %s\nReason: %s\nReference: %s\nExpiry: %s' % (kind,value,classification,reason,reference,expiry or 'none')
  if not self.yes('Allowlist Add',summary+'\n\nAdd this allowlist entry?'):
   return
  cmd=[sys.executable,str(self.current/'sharing_allowlist_manager.py'),'--root',str(self.root),'add','--type',kind,'--value',value,'--classification',classification,'--reason',reason,'--reference',reference]
  if expiry:
   cmd+=['--expires-at',expiry]
  self.cmd('Allowlist Add',cmd,timeout=60)
 def sharing_allowlist_remove(self):
  eid=self.ask('Allowlist Remove','Entry ID','').strip()
  if eid and self.yes('Allowlist Remove','Remove allowlist entry '+eid+'?'):self.cmd('Allowlist Remove',[sys.executable,str(self.current/'sharing_allowlist_manager.py'),'--root',str(self.root),'remove',eid],timeout=60)
 def sharing_allowlist_toggle(self):
  eid=self.ask('Allowlist Toggle','Entry ID','').strip()
  if eid:self.cmd('Allowlist Toggle',[sys.executable,str(self.current/'sharing_allowlist_manager.py'),'--root',str(self.root),'toggle',eid],timeout=60)
 def sharing_allowlist_menu(self):
  self.menu('Approved Sharing Allowlist',[('Show entries',self.sharing_allowlist_list),('Add email/domain',self.sharing_allowlist_add),('Remove entry',self.sharing_allowlist_remove),('Enable/disable entry',self.sharing_allowlist_toggle)],'Exact email/domain matching | audited | fail closed')
 def retention_policy_show(self):
  tool=self.current/'retention_policy_manager.py';self.cmd('Retention Policy',[sys.executable,str(tool),'--root',str(self.root),'show'],timeout=60)
 def retention_policy_edit(self):
  tool=self.current/'retention_policy_manager.py';values=[]
  fields=[('live_completed_seconds','Live completed visibility seconds','30'),('completed_history_days','Completed history days','7'),('failed_history_days','Failed history days','30'),('raw_audit_days','Raw audit days','14'),('sanitized_audit_days','Sanitized audit days','90')]
  for key,label,default in fields:
   value=self.ask('Retention Policy',label,default).strip()
   if not value.isdigit():return self.text('Retention Policy','Invalid integer for '+label)
   values.extend(['--'+key.replace('_','-'),value])
  self.cmd('Save Retention Policy',[sys.executable,str(tool),'--root',str(self.root),'set',*values],timeout=60)
 def retention_policy_preview(self):
  tool=self.current/'retention_policy_manager.py';self.cmd('Retention Cleanup Preview',[sys.executable,str(tool),'--root',str(self.root),'preview'],timeout=300)
 def retention_policy_apply(self):
  tool=self.current/'retention_policy_manager.py'
  if self.yes('Retention Cleanup','Apply configured retention policy and delete eligible files/history?'):self.cmd('Apply Retention Cleanup',[sys.executable,str(tool),'--root',str(self.root),'apply','--confirm'],timeout=300)
 def retention_policy_menu(self):
  self.menu('Retention Policy',[('Show current policy',self.retention_policy_show),('Edit policy',self.retention_policy_edit),('Preview cleanup',self.retention_policy_preview),('Apply cleanup',self.retention_policy_apply)],'Validated bounds | preview before apply | retryable states protected')
 def feature_dashboard(self):
  tool=self.current/'feature_control.py'
  if not tool.is_file():return self.text('Feature Control Center','feature_control.py is not installed.')
  r=subprocess.run([sys.executable,str(tool),'--root',str(self.root),'show'],text=True,capture_output=True,timeout=60)
  try:data=json.loads(r.stdout)
  except Exception:return self.text('Feature Control Center',(r.stdout+'\n'+r.stderr).strip())
  lines=[f"Profile: {data.get('profile')} | Revision: {data.get('revision')}",'',f"{'FEATURE':32} {'CONFIG':9} {'EFFECTIVE':10} REASON"]
  for key,val in (data.get('effective') or {}).items():lines.append(f"{key:32} {('ON' if val.get('configured') else 'OFF'):9} {('ON' if val.get('effective') else 'OFF'):10} {val.get('reason') or '-'}")
  ai=self.current/'ai_health.py'
  if ai.is_file():
   q=subprocess.run([sys.executable,str(ai),'--root',str(self.root)],text=True,capture_output=True,timeout=20)
   try:
    a=json.loads(q.stdout);lines.extend(['','AI STATUS',f"Local AI : {a['local_ai'].get('provider')} | {a['local_ai'].get('model')} | {a['local_ai'].get('mode')} | reachable={a['local_ai'].get('reachable')}",f"Gemini   : {a['gemini'].get('preferred_model')} | {a['gemini'].get('mode')} | credential={'YES' if a['gemini'].get('credential_configured') else 'NO'}"])
   except Exception:pass
  self.text('Feature & AI Dashboard','\n'.join(lines))
 def feature_profile(self):
  value=self.choose('Apply Operating Profile',['FULL_AUTOMATION','JIRA_INTAKE_ONLY','PRIVACY_LOCAL_AI_ONLY','AI_ANALYSIS_NO_AUTO_ACTION','MAINTENANCE_SAFE_MODE'],'Select profile; dependency rules are applied automatically')
  if value is None:return
  if self.yes('Apply Operating Profile',f'Apply {value}? This affects the next polling cycle and new tickets only.'):self.cmd('Apply Operating Profile',[sys.executable,str(self.current/'feature_control.py'),'--root',str(self.root),'profile',value],timeout=60)
 def feature_toggle(self):
  features=['jira_polling','siem_retrieval','privacy_sanitization','local_ai_detection','gemini_analysis','virustotal_enrichment','sharing_allowlist','telegram_notification','status_web_viewer','documentation_viewer']
  key=self.choose('Configure Individual Feature',features,'Select feature')
  if key is None:return
  state=self.choose('Feature State',['OFF','ON'],f'Select state for {key}')
  if state is None:return
  if self.yes('Feature Change',f'Set {key} to {state}? Effective dependencies will be recalculated.'):self.cmd('Feature Change',[sys.executable,str(self.current/'feature_control.py'),'--root',str(self.root),'set',key,state],timeout=60)
 def feature_control_menu(self):
  self.menu('Feature Control Center',[('Feature & AI dashboard',self.feature_dashboard),('Apply operating profile',self.feature_profile),('Configure individual feature',self.feature_toggle),('Show raw effective configuration',lambda:self.cmd('Effective Feature Configuration',[sys.executable,str(self.current/'feature_control.py'),'--root',str(self.root),'show']))],'Selection-first | changes apply to next polling cycle | Web Viewer remains read-only')
 def maintenance(self):
  common=[
   sys.executable,
   str(self.manager/'cleanup_manager.py'),
   '--root',str(self.root),
   '--keep-applied','3',
   '--keep-failed','3',
   '--max-age-days','30',
  ]
  self.menu(
   'Maintenance',
   [
    (
     'Retry queue and manual review',
     self.retry_queue_status,
    ),
    (
     'Approved sharing allowlist',
     self.sharing_allowlist_menu,
    ),
    (
     'Retention policy management',
     self.retention_policy_menu,
    ),
    (
     'Ticket reprocessing',
     self.ticket_reprocessing_menu,
    ),
    (
     'Secret scan and safe installer',
     self.secret_scan_menu,
    ),
    (
     'Cleanup preview',
     lambda:self.cmd(
      'Cleanup Preview',
      common+['--dry-run'],
     ),
    ),
    (
     'Run cleanup',
     lambda:self.yescmd(
      'Cleanup',
      'Apply retention cleanup?',
      common,
     ),
    ),
    (
     'List backups',
     lambda:self.text(
      'Backups',
      '\n'.join(
       p.name
       for p in sorted(
        self.backups.glob('*.tar.gz'),
        reverse=True,
       )
      )
      or 'No backups',
     ),
    ),
    (
     'TUI activity log',
     lambda:self.text(
      'TUI Activity',
      '\n'.join(
       self.activity.read_text(
        errors='replace'
       ).splitlines()[-300:]
      )
      if self.activity.exists()
      else 'No activity',
     ),
    ),
    (
     'Fix permissions',
     self.permissions,
    ),
   ],
   'Persistent retry state and local maintenance',
  )
 def permissions(self):
  os.chmod(self.shared,0o700)
  if (self.shared/'.env').exists():os.chmod(self.shared/'.env',0o600)
  for p in [self.activity,*self.backups.glob('*')]:
   if p.exists() and p.is_file():os.chmod(p,0o600)
  self.log('permissions_fixed'); self.text('Permissions','Shared: 700\n.env, backups, activity log: 600\nPASS')
 def help(self):self.text('User Guide',(self.current/'TUI_USER_GUIDE.md').read_text() if (self.current/'TUI_USER_GUIDE.md').exists() else 'Guide not installed')
 def run(self):
  self.log('tui_started',details={'version':VERSION}); items=[('[1] Dashboard',self.dashboard),('[2] Runtime control',self.runtime),('[3] Update manager',self.update),('[4] Audit viewer',self.audits),('[5] Log viewer',self.logview),('[6] Diagnostics',self.diagnostics),('[7] Viewer service',self.viewer),('[8] Release and rollback',self.releases),('[9] Maintenance',self.maintenance),('[F] Feature Control Center',self.feature_control_menu),('[H] Help / User guide',self.help)]; p=0
  while 1:
   h,w=self.frame('Main Menu',f'Release {(self.current/"VERSION").read_text().strip()} | TUI {VERSION} | Web GUI remains read-only')
   for i,(name,_) in enumerate(items):self.s.addnstr(5+i,4,('▶ ' if i==p else '  ')+name,w-8,(self.c(5)|curses.A_BOLD) if i==p else self.c(1)|curses.A_BOLD)
   self.s.addnstr(17,4,'[0] Exit',w-8,self.c(3)); self.foot('Up/Down + Enter | 1-9 shortcuts | 0/Q exit'); k=self.getkey()
   if k in (ord('0'),ord('q'),ord('Q')):self.log('tui_exited');return
   if k in (curses.KEY_DOWN,ord('j')):p=(p+1)%len(items)
   elif k in (curses.KEY_UP,ord('k')):p=(p-1)%len(items)
   elif k in (10,13):items[p][1]()
   elif ord('1')<=k<=ord('9'):items[k-ord('1')][1]()
   elif k in (ord('f'),ord('F')):self.feature_control_menu()
   elif k in (ord('h'),ord('H')):self.help()
def main():
 a=argparse.ArgumentParser(); a.add_argument('--root',type=Path,default=Path.home()/'SOC-Automation'); x=a.parse_args(); curses.wrapper(lambda s:TUI(s,x.root).run())
if __name__=='__main__':main()
SAFE_BUILDER_V2_B85='c-pO4ZExc?68`RAp=%eQw2|d)itXLm5DsplwC-k;AoecMIzEAxXj_fmB2tN8;{NuVAu0Ja$)dOqiA8caGn|=cX2|dV(JFb-8b@i1rH@9w5VI`(u`wyK#PIz|DawNRz7ZvPRtSTpX(p(MvXnQfsbZSbf-`$Y`7Dmc_MbdU?Tp(6v-zwPQEUsA<dZ07_A-*cihE84(pRi+V5k;CDwv28R;^TH8~-h{lr<XX-qr8^P4{-tcUQ!jMuOPH_wz+SgBhp`BU*-$@Z)UCVW5A;G`KHw{Bj=Qu<*-gv|u586f9<xGfvhO@4>*kz3RKef;mB!<e;`Whch`n%a~+^F*l;r7#8Ht8Pj|7KkYl``JF{<oX88-R9|BTr1hZ4?pZ1af4$R`i$H$;_s#)*^dvC5XN%{YCC~W}r_cFh{>&fZNHG2L<8wHEMkB}1a4zc|8I2l!@9fqayr4Dk4ziG$))Do8_I~MI8N+V#4`cNH=C=2>JMfH8-tVYNx3{Fj56yqWB5f}H=4f^L!CvFaI1{)qTK&sjw})yS#@i&**)Y!_vPS;a`ewQNsn^xKN2?!xTH_%G*Ejw}@6tn`e)Vqqz3VIR%&m9nb^D%!Czg(SD5HWUEEU`lb0I0Z=bt?%K|h{fpMCl4T@AVe*zI@E&b*sJ_v*~^&wlmJK3(?u1EgCw2DhG+^BA!wR`?u)I)MFQ7VzB>{0PPcM#ksvRreR~wpManMsWx+7SPy-XbxuJPz<Up2t=&DLzc(c!cS;Qr>szO0fbsw=DU-y$q%wr6j|(xGSZWRrr~(uKV`*zMX1E-cs=0JguN)D6xk!3>p(<8xv0iU{Ye?e`V3JD0^?Y%uN#e!O$<PYnOp6GK_W;Ejd2HNPe1--=1#$A=#Lj*A=9#)8JmaE6s%=ha&ySih=sVnVQ3CCU6?ZXHW1zfWbQyJ5!^Ch0tpL;Gg<^Q5R}q{sn9L9cB^n#!gxSaAJdDHH+FZmt2G$H@u&bRq)x~bFgASmfMi4yqgG;Ujg%m;eIQs^Il&CdqJVfrsaYx9;iw@Q=EzX5IRM-uj0zKpkZbNlTxn~;Q9}cc$jiwjn!7GR^P>sWsgX+!4V(rPqtg<MII|#M@4^$m`qOCfudWAP-#2^b&)$`FC$XVzsKh}U-|`M<?a(}DDUOu#wPXYe>KwZIC@ox4hY0Zy>QunOIB|_(zBzj66w^2xo8&#QjvaYNhf(bx;IwOI9mJ;ot%Gr>Ct9h}7-jB26or~Kk@d3p4UO`!27=FnBFZ6{D~W`V?~m5YyY!`!c9-tgNnI3qInIkLV4T~0!SB-CttgysF)cB{-QWm}+sPdohCbEPCTTW{EQ8bsy3#ThF8Qm~zdmbr0riQj&cy0aSE31W1nh(O@8A{}RWhlA-<HGXIT)gpG5{+)iyy%_oiW6;BJ`!be1B^dd4djisfj#Vo5E>1$vuXGTIcSdD4EUX5f^@TFGp5K@6qP2w;ZR^wfO}i$ZoEQnzl$z7jZ_zmR6-z)ecMHU$8m2(BT4n38xDoJ-K_jw}2Zs3KJF=j+DgF>onrb=r15;Cf+;(!w<lgOc;8jL1UD#Fw~B=K~6x5iA*f(E>(_(It)QlFm_y9bRv*<UMH?BX73u%2E%ZF*D`l0;8Y(_BbIbTlItm_N=PYtlJicP#!-52CK2aRI^9?p*Z3mAMPFp<RC2O_nnnYe_COkTQWbC6RdqIz?G$Bd4k5h3rVMHl9YYgHnh6vi)qtV7@XH$6(6|Ma=mQR#tVIxad6W~&CK{x`t63;csAB7|L)c{wNGl=)QBPMpNR8lr=op1EFHiu^Wgd_fQih`qSqa)FL^5V@ZA91HwevQLw2$0fk73+$0H|9PjTU)5ToHg=mXxPR%#5m)b_NX73N04raMnO%#lnQX6YGa;1F%3eIh{cB3E7StBE%dH2cBwZi_mIK$ZpnXKCZNS>*mFm%gbi(sz2ynUXqR}cOC}sG0<BF)cbhfp$4_;it$=yH4t^OrpKV{Bg2@imOBsb3ku>#=Rqf}Z^%$vFg!JL`$0RPs*VrG)jg<CsP2JIl^I&95`UAd%9J|Tu`{rorvkbO6)5|a%Iaj?31&$a9@%Ms$o~29BeF%z)&U3uz$Z=em=RUi)r`)9wGPmpPNHe;#XV!e9(#wdwapiWj%g?ZdCP!Eztts3yX|%ga!U3Zb+-b1DjTf`Qjs>Ie>XHFYs<n51I3#|n<xf8nx3pJ$rcrvMMA2w-97$I37iGcDEPX&gv3;RwLyp!3FiRbM+(c&UwW74#?P16XP>-tEF^f{al$gmIh2BM*gpL*vXBD=Q8d94wjvy|T0(sdS<*g*9G2&C6sQ)Ujp#OhiwbINAZ}bhVlb-ISI9)Hx9bmmFM!KKo&m1~@PR%7z9P}20Uo}I7HPu%>?wvA!RrQ?0C4~*v|ZiSoiuwgs~fvhiU9ks3@i?cz*SV5m6P^rz21okNU%)D?p9zNjf~0^L(OY6Jmw&WaySW(=B715qsf~K_*33%;8GMV!MjlD1XXF*$C>pO^eQpx2D*d3Ehkk}c9e!#8BPI;m~qR5y96qV^Jf;N=H$DT61+By)f?KbzkAy(dnU0?P*k0N`@eSKto<*a`@3qRQW#6v_P?DHmoCtKbFFZeP@RFdtXBHH$N3}5FHpgyO`eEd&-QNobMNA^JMhkBk)qPe-xdq|!9djkA&=?}i1QQDA}4Q{S)%H=wp&VpH0t0xz!IzS5dgzsKxe_GpvA(N&<Gm~WUVg5F1mdQr4emuF12?09t~&OcF%;Y)FuoPMY;yJA~R?&u-{+d%YY~WKIEp`?;k~RPJ??ms>)nT%dR6|@m2uzgRF$Ur5&@>Jb)AIVe=p^LqN99WFT=!-s6+kdl33wK6R-t{nVug>ZuC{DktJA3UqW~8OS7r+A}hOx&0JlY^4}ulVaBL?AU#MdnwoS$Kk3BxeZp;6~0EYd1c7&rx0kHcCe~!N5d$WVYJlu{^eE_?Ub3iiolv*N0O>k_4QUo1DeFFnhe>^rB-97N<JK|Vd<;YaO^H+2dbI9^dwTFZ|hy;En$0waV;NXjz%&v#)~;HG*}E6BNyG?CD{w-T-J{?g!>BY1lslg-`kx7jDI*#?o`D@LLs%IKj<rWc=~tl@CSP!edMJ$x}+?y#jt+PYhuvqbzQ}d?3YB9nXS&;rF-uOa=(hVxub*sg*Su-nriMSuqc+*8%hlz&1jqEC3Y3m8kGm;jxxlNL|oa((Dy)@h1Er_QvH?34_nhH9&hRc>i7~vzVEuk_c0QDpR`p(H2w#Hv$SC'

