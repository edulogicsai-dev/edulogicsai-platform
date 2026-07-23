import { createClient } from '@/utils/supabase/server';
import { NextResponse } from 'next/server';
import { NextRequest } from 'next/server';
import { getErrorRedirect, getStatusRedirect } from '@/utils/helpers';
import { getStudentProfile, DOMAIN_ID } from '@/utils/supabase/profile';

export async function GET(request: NextRequest) {
  // The `/auth/callback` route is required for the server-side auth flow implemented
  // by the `@supabase/ssr` package. It exchanges an auth code for the user's session.
  const requestUrl = new URL(request.url);
  const code = requestUrl.searchParams.get('code');

  const supabase = await createClient();

  if (code) {
    const { error } = await supabase.auth.exchangeCodeForSession(code);

    if (error) {
      return NextResponse.redirect(
        getErrorRedirect(
          `${requestUrl.origin}/signin`,
          error.name,
          "Sorry, we weren't able to log you in. Please try again."
        )
      );
    }
  }

  // FR2 (auth-flow): this route completes email-confirmation and magic-link
  // signins -- same post-auth gate as signUp/signInWithPassword, not the
  // Stripe starter's original unconditional '/account' redirect.
  const {
    data: { user }
  } = await supabase.auth.getUser();
  const destination = user
    ? (await getStudentProfile(supabase, user.id, DOMAIN_ID))
      ? '/dashboard'
      : '/onboarding'
    : '/signin';

  return NextResponse.redirect(
    getStatusRedirect(
      `${requestUrl.origin}${destination}`,
      'Success!',
      'You are now signed in.'
    )
  );
}
