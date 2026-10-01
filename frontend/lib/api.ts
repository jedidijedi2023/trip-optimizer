export const staticDeploy = process.env.NEXT_PUBLIC_STATIC_DEPLOY === 'true';
export const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || (staticDeploy ? '' : 'http://127.0.0.1:8000');
export const apiAvailable = apiBaseUrl.length > 0;
