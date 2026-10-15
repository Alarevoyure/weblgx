# -*- coding: utf-8 -*-
# Part of Web@LGX. See LICENSE file for full copyright and licensing details.

RELEASE_LEVELS = [ALPHA, BETA, RELEASE_CANDIDATE, FINAL] = ['alpha', 'beta', 'candidate', 'final']
RELEASE_LEVELS_DISPLAY = {ALPHA: ALPHA,
                          BETA: BETA,
                          RELEASE_CANDIDATE: 'rc',
                          FINAL: ''}

# version_info format: (MAJOR, MINOR, MICRO, RELEASE_LEVEL, SERIAL)
# inspired by Python's own sys.version_info, in order to be
# properly comparable using normal operators, for example:
#  (6,1,0,'beta',0) < (6,1,0,'candidate',1) < (6,1,0,'candidate',2)
#  (6,1,0,'candidate',2) < (6,1,0,'final',0) < (6,1,2,'final',0)
version_info = (17, 0, 0, FINAL, 0, '')
# Keep internal compatibility markers in version_info/series, but expose a
# forked product version for UI/log display.
version = '1.0'
series = serie = major_version = '.'.join(str(s) for s in version_info[:2])

product_name = 'Web@LGX'
description = 'Web@LGX Server'
long_desc = '''Web@LGX est une solution dédiée exclusivement à la création et à la gestion de sites internet
professionnels. Issu d'une architecture robuste, l'outil a été épuré pour se concentrer sur 
l'essentiel : une expérience de design fluide et une performance optimale.
'''
classifiers = """Development Status :: 5 - Production/Stable
License :: OSI Approved :: GNU Lesser General Public License v3

Programming Language :: Python
"""
url = 'https://www.loegaux.fr'
author = 'LOEGAUX - Propriété de Ferme 201 SARL'
author_email = 'contact@loegaux.fr'
license = 'LGPL-3'

nt_service_name = "weblgx"

version += '-20260708'
