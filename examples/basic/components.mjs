export function components({element}) {
  return {
    Aside: ({title, children}) => element('aside', {},
      element('h2', {}, title), children)
  };
}
