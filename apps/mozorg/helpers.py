"""
Download buttons. Let's get some terminology straight. Here is a list
of terms and example values for them:

* product: 'firefox' or 'thunderbird'
* version: 7.0, 8.0b3, 9.0a2
* build: 'beta', 'aurora', or None (for latest)
* platform: 'os_windows', 'os_linux', or 'os_osx'
* locale: a string in the form of 'en-US'
"""

import jinja2
import jingo
from django import shortcuts

from product_details import product_details

download_urls = {
    'transition': '/products/download.html',
    'direct': 'http://download.mozilla.org/',
    'aurora': 'http://ftp.mozilla.org/pub/mozilla.org/firefox/nightly/latest-mozilla-aurora',
    'aurora-l10n': 'http://ftp.mozilla.org/pub/mozilla.org/firefox/nightly/latest-mozilla-aurora-l10n'
}

locales_using_transition = []

def latest_aurora_version(locale):
    builds = product_details.firefox_primary_builds
    vers = product_details.firefox_versions['FIREFOX_AURORA']

    if locale in builds and vers in builds[locale]:
        return vers, builds[locale]


def latest_beta_version(locale):
    builds = product_details.firefox_primary_builds
    vers = product_details.firefox_versions['LATEST_FIREFOX_DEVEL_VERSION']

    if locale in builds and vers in builds[locale]:
        return vers, builds[locale]


def latest_version(locale):
    beta_vers = product_details.firefox_versions['FIREFOX_AURORA']
    aurora_vers = product_details.firefox_versions['LATEST_FIREFOX_DEVEL_VERSION']
    
    def _check_builds(builds):
        if locale in builds and isinstance(builds[locale], dict):
            # The json should be already ordered in increasing
            # order. The previous PHP code assumed this, so it should
            # work.
            for version, info in reversed(builds[locale].items()):
                if version == beta_vers or version == aurora_vers:
                    continue
                if info:
                    return version, info

    return (_check_builds(product_details.firefox_primary_builds) or
            _check_builds(product_details.firefox_beta_builds))

def make_aurora_link(product, version, platform, locale):
    # Download links are different for localized versions
    src = 'aurora' if locale.lower() == 'en-us' else 'aurora-l10n'

    filename = {
        'os_windows': 'win32.installer.exe',
        'os_linux': 'linux-i686.tar.bz2',
        'os_osx': 'mac.dmg'
    }[platform]

    return ('%s/%s-%s.%s.%s' %
            (download_urls[src], product, version, locale, filename))

def make_download_link(product, build, version, platform, locale, 
                       force_direct=False):
    # Aurora has a special download link format
    if build == 'aurora':
        return make_aurora_link(product, version, platform, locale)

    # The downloaders expect the platform in a certain format
    platform = {
        'os_windows': 'win',
        'os_linux': 'linux',
        'os_osx': 'osx'
    }[platform]

    # Figure out the base url. certain locales have a transitional
    # thankyou-style page (most do)
    src = 'direct'
    if locale in locales_using_transition and not force_direct:
         src = 'transition'

    return ('%s?product=%s-%s&os=%s&lang=%s' %
            (download_urls[src], product, version, platform, locale))

@jingo.register.function
@jinja2.contextfunction
def download_button(ctx, locale, build=None):
    def latest(locale):
        if build == 'aurora':
            return latest_aurora_version(locale)
        elif build == 'beta':
            return latest_beta_version(locale)
        else:
            return latest_version(locale)

    version, platforms = latest(locale) or latest('en-US')

    # Gather data about the build for each platform
    builds = []
    for platform in ['Windows', 'Linux', 'OS X']:
        # Fallback to en-US if this platform/version isn't available
        # for the current locale
        _locale = locale
        if platform not in platforms:
            _locale = 'en-US'

        # Normalize the platform name
        platform = 'os_%s' % platform.lower().replace(' ', '')

        # And generate all the info
        download_link = make_download_link('firefox', build, version,
                                           platform, locale)
        download_link_direct = make_download_link('firefox', build, version,
                                                  platform, locale, True)
        builds.append({'platform': platform,
                       'download_link': download_link,
                       'download_link_direct': download_link_direct})

    # Get the native name for current locale
    langs = product_details.languages
    locale_name = langs[locale]['native'] if locale in langs else locale

    data = {
        'locale_name': locale_name,
        'version': version,
        'product': 'firefox',
        'builds': builds
    }

    html = jingo.render_to_string(ctx['request'],
                                  'mozorg/download_button.html',
                                  data)
    return jinja2.Markup(html)
