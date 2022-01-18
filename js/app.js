$(function() 
{
    // Open / close settings
    $( "#settings-btn" ).on( "click", function() {
      $( ".sheet-overlay" ).addClass( "sheet-overlay-active" )
      $( ".sheet" ).addClass( "sheet-active" )
    })

    $( ".sheet-overlay, #settings-close-btn" ).on( "click", function() {
      $( ".sheet-overlay" ).removeClass( "sheet-overlay-active" )
      $( ".sheet" ).removeClass( "sheet-active" )
    })
})