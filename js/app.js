$(function() 
{
    /**
     * Open / close settings
     */
    $( "#settings-btn" ).on( "click", function() {
        $( ".sheet-overlay" ).addClass( "sheet-overlay-active" )
        $( ".sheet" ).addClass( "sheet-active" )
    })

    $( ".sheet-overlay, #settings-close-btn" ).on( "click", function() {
        $( ".sheet-overlay" ).removeClass( "sheet-overlay-active" )
        $( ".sheet" ).removeClass( "sheet-active" )
    })


    /**
     * Handle settings form changes
     * @param {string} units The units to set the values to (metric || imperial)
     */ 
    function setUnits(units)
    {
        if (units === "metric") {
            $("#settings-form .unit").text("mm")
            $("#settings-form #disk-diameter").prop("step", "1")
            $("#settings-form #disk-thickness").prop("step", "0.1")
        } else if (units === "imperial") {
            $("#settings-form .unit").text("in")
            $("#settings-form #disk-diameter").prop("step", "0.1")
            $("#settings-form #disk-thickness").prop("step", "0.01")
        }
    }

    function saveSettings()
    {
        var  formData = []

        // Remove old formData
        localStorage.removeItem('settings')

        // Loop through form input fields
        $("#settings-form input[type=number], #settings-form select, #settings-form input[type=radio]:checked").each(function() {
            formData.push({ 
                name: this.name, 
                value: $(this).attr('type') === "radio" ? this.id : this.value,
                type: $(this).attr('type')
            })
        })

        // Convert array to JSON and story in localStorage
        localStorage.settings = JSON.stringify(formData)
    }

    function loadSettings()
    {
        if (localStorage.settings != undefined) {
            settings  = JSON.parse(localStorage.settings)
            for (var i = 0; i < settings.length; i++) {
                if (settings[i].type != undefined && settings[i].type == "radio")
                {
                    $("#" + settings[i].value).prop('checked', true)
                } else {
                    $("[name=" + settings[i].name + "]").val(settings[i].value)
                }

                if (settings[i].name === "units")
                {
                    setUnits(settings[i].value)
                }
            }
        } else {
            setUnits("metric")
        }
    }
    
    // Get form data from localstorage on page load
    loadSettings()

    // Listen for changes in the settings form
    let timeout = 0;

    $("#settings-form input, #settings-form select").on( "input", function() {
        // Don't save settings on every change immediately, but wait a little to batch them
        clearTimeout(timeout);

        timeout = setTimeout(function() {
            saveSettings()
        }, 3000)
    });

    $("#settings-form input[name=units]").on( "change", function() {
        setUnits(this.id)
    })
})