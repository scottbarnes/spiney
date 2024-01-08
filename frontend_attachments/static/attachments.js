document.addEventListener('DOMContentLoaded', function () {
    let skip = 0;
    const limit = 10;
    const attachmentsList = document.getElementById('attachments-list');
    const loadingIndicator = document.getElementById('loading');

    async function fetchAttachments() {
        loadingIndicator.style.display = 'block';
        const response = await fetch(`/attachments/?skip=${skip}&limit=${limit}`);
        const attachments = await response.json();
        attachments.forEach(attachment => {
            const imageElement = document.createElement('img');
            imageElement.src = attachment.url;
            imageElement.className = 'img-fluid'; // Bootstrap class for responsive images
            imageElement.alt = 'Attachment Image'; // Alt text for accessibility

            const listItem = document.createElement('div');
            listItem.className = 'list-group-item';
            listItem.appendChild(imageElement); // Append the image to the list item
            attachmentsList.appendChild(listItem);
        });
        skip += limit;
        loadingIndicator.style.display = 'none';
    }

    function isInViewport(element) {
        const rect = element.getBoundingClientRect();
        return (
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight)
        );
    }

    window.addEventListener('scroll', () => {
        if (isInViewport(loadingIndicator)) {
            fetchAttachments();
        }
    });

    fetchAttachments();
});
