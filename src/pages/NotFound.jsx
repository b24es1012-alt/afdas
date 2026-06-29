import ErrorPage from '../components/common/ErrorPage';

export default function NotFound() {
  return (
    <ErrorPage
      code={404}
      title="Page Not Found"
      message="The page you're looking for doesn't exist or has been moved."
      showRetry={false}
    />
  );
}
