declare global {
  interface Window {
    AppleID?: AppleIDNamespace
  }
}

type AppleSignInResponse = {
  authorization?: {
    id_token?: string
  }
}

type AppleIDNamespace = {
  auth?: {
    init: (options: {
      clientId: string
      scope: string
      redirectURI: string
      usePopup: boolean
    }) => void
    signIn: () => Promise<AppleSignInResponse>
  }
}

let appleScriptPromise: Promise<void> | null = null

const loadAppleScript = (): Promise<void> => {
  if (window.AppleID?.auth) {
    return Promise.resolve()
  }

  if (appleScriptPromise) {
    return appleScriptPromise
  }

  appleScriptPromise = new Promise((resolve, reject) => {
    const existingScript = document.querySelector<HTMLScriptElement>(
      'script[data-apple-identity="true"]'
    )

    if (existingScript) {
      existingScript.addEventListener('load', () => resolve(), { once: true })
      existingScript.addEventListener(
        'error',
        () => reject(new Error('Failed to load Apple Sign in script')),
        { once: true }
      )
      return
    }

    const script = document.createElement('script')
    script.src = 'https://appleid.cdn-apple.com/appleauth/static/jsapi/appleid/1/en_US/appleid.auth.js'
    script.async = true
    script.defer = true
    script.dataset.appleIdentity = 'true'
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('Failed to load Apple Sign in script'))
    document.head.appendChild(script)
  })

  return appleScriptPromise
}

export const initAppleSignIn = async (clientId: string, redirectUri: string): Promise<void> => {
  await loadAppleScript()

  window.AppleID?.auth?.init({
    clientId,
    scope: 'name email',
    redirectURI: redirectUri,
    usePopup: true
  })
}

export const requestAppleIdentityToken = async (
  clientId: string,
  redirectUri: string
): Promise<string> => {
  await initAppleSignIn(clientId, redirectUri)

  const appleResponse = await window.AppleID?.auth?.signIn()
  const identityToken = appleResponse?.authorization?.id_token

  if (!identityToken) {
    throw new Error('Apple did not return an identity token. Please try again.')
  }

  return identityToken
}

export const isAppleSignInCancellation = (error: any): boolean => {
  return error?.error === 'popup_closed_by_user'
    || error?.error === 'user_cancelled_authorize'
}
