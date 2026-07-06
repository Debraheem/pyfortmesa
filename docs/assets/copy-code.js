(function () {
  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }

    var textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.setAttribute('readonly', '');
    textArea.style.position = 'fixed';
    textArea.style.top = '-1000px';
    document.body.appendChild(textArea);
    textArea.select();

    try {
      document.execCommand('copy');
      return Promise.resolve();
    } catch (error) {
      return Promise.reject(error);
    } finally {
      document.body.removeChild(textArea);
    }
  }

  function addCopyButton(pre) {
    if (pre.classList.contains('pyfortmesa-code-block')) {
      return;
    }

    var code = pre.querySelector('code');
    if (!code) {
      return;
    }

    pre.classList.add('pyfortmesa-code-block');

    var button = document.createElement('button');
    button.className = 'pyfortmesa-copy-code';
    button.type = 'button';
    button.textContent = 'copy';
    button.setAttribute('aria-label', 'Copy code block');

    button.addEventListener('click', function () {
      copyText(code.innerText).then(function () {
        button.textContent = 'copied';
        window.setTimeout(function () {
          button.textContent = 'copy';
        }, 1400);
      }).catch(function () {
        button.textContent = 'failed';
        window.setTimeout(function () {
          button.textContent = 'copy';
        }, 1400);
      });
    });

    pre.appendChild(button);
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('pre').forEach(addCopyButton);
  });
}());
