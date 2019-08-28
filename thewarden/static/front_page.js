setTimeout(function () {
    $('.svg-wrapper').each(function () {
        var wrapper = $(this);
        var svg = wrapper.find('svg');
        var text = svg.find('text');
        var bbox = text.get(0).getBBox();

        svg.get(0).setAttribute('viewBox',
            [bbox.x,
            bbox.y,
            bbox.width,
            bbox.height].join(' '));
        wrapper.css('padding-top', (bbox.height / bbox.width) * 100 + '%');
    });
}, 100);
