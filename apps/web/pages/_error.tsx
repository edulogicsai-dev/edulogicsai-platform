function Error() {
  return null;
}
Error.getInitialProps = () => ({ statusCode: 500 });
export default Error;
